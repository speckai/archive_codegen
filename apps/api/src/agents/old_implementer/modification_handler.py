import traceback
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Type

from llmxml import generate_prompt_template, parse_xml
from morphcloud.api import InstanceExecResponse
from pydantic import BaseModel, Field
from src.agents.implementer.merging import merge_changes
from src.config import DEV
from src.prompts import (
    CLASSIFY_ERRORS_SYSTEM_PROMPT,
    CLASSIFY_ERRORS_USER_PROMPT,
    CREATE_FILE_USER_PROMPT,
    EDIT_FILE_USER_PROMPT,
    INJECT_SYSTEM_PROMPT,
    INJECT_USER_PROMPT,
    RUN_COMMAND_USER_PROMPT,
    RUN_COMMAND_WITH_ERRORS_USER_PROMPT,
)
from src.schemas.core.common import (
    ExistingFileModification,
    FileObject,
    Image,
    NewFileModification,
    ProjectDependencies,
    TerminalCommandModification,
)
from src.schemas.core.common.modifications import DeleteFileModification, RestartWebsite
from src.schemas.core.implementer import (
    AttemptedCommandResponse,
    CannotFullfillStep,
    CreateFileResponse,
    EditFileResponse,
    ErrorClassification,
    FollowUpStep,
    MiniStepRepr,
    MiniStepsPerformedHistory,
    NewCommandResponse,
    RunCommandResponse,
)
from src.schemas.llm import EndStream, Model, PartialStream
from src.utils.logging import logger

MAX_COMMAND_ATTEMPTS: int = 5

if TYPE_CHECKING:
    from src.agents.implementer.implementer_agent import ImplementerAgent
    from src.agents.utils.task.task import Task


class ModificationHandler:
    def __init__(self, task: "Task", implementer_agent: "ImplementerAgent"):
        self.task = task
        self.implementer_agent = implementer_agent

    async def handle_run_command(
        self,
        modification: TerminalCommandModification,
        step_index: int,
        system_prompt: str,
        steps_so_far: MiniStepsPerformedHistory,
        project_dependencies: ProjectDependencies,
    ) -> int:
        response_generator = self._retry_llm_response(
            system=system_prompt,
            message=RUN_COMMAND_USER_PROMPT(
                purpose=modification.purpose,
                thinking=modification.thinking,
                command=modification.command,
                task_context=self.task.current_workflow.context.xml,
                dependencies_xml=project_dependencies.xml,
                special_instructions_to_follow=self.task.current_workflow.context.custom_rules,
            )
            + f"\n\n{generate_prompt_template(RunCommandResponse)}",
            response_model=RunCommandResponse,
        )
        parsed_response: RunCommandResponse | None = None
        async for event in response_generator:
            if event["type"] == "end":
                parsed_response = event["model"]
                break

        if not parsed_response:
            logger.error("Failed to get valid response for run_command")
            return step_index

        command: str = parsed_response.command
        command_result: InstanceExecResponse = await self.task.terminal.run_command(
            command=command
        )
        output: str = command_result.stdout
        errors: str = command_result.stderr
        logger.debug(f"ImplementerAgent: Command output: {output}")
        logger.debug(f"ImplementerAgent: Command errors: {errors}")

        did_error: bool = False
        attempts: int = 1
        previous_errors: list[AttemptedCommandResponse] = []

        async def _classify_errors(
            attempted_command: str, output: str, errors: str
        ) -> ErrorClassification:
            if not errors:  # TODO: Fix with prompt
                return ErrorClassification(
                    thinking="No errors found", command_is_not_as_intended=False
                )

            response: ErrorClassification = await self.implementer_agent.llm_response(
                system=CLASSIFY_ERRORS_SYSTEM_PROMPT(),
                message=CLASSIFY_ERRORS_USER_PROMPT(
                    purpose=modification.purpose,
                    thinking=modification.thinking,
                    attempted_command=attempted_command,
                    output=output,
                    errors=errors,
                ),
                response_model=ErrorClassification,
                model_type=Model.GEMINI_2_0_FLASH,
            )
            return response

        initial_error_classification: ErrorClassification = await _classify_errors(
            command, output, errors
        )
        did_error: bool = initial_error_classification.command_is_not_as_intended

        last_attempted_command: AttemptedCommandResponse = AttemptedCommandResponse(
            attempted_command=command,
            agent_thinking=parsed_response.thinking,
            output=output,
            errors=errors,
        )

        while did_error and attempts < MAX_COMMAND_ATTEMPTS:
            logger.debug(f"Attempting command: {command}")
            attempts += 1
            new_command_response: NewCommandResponse = (
                await self.implementer_agent.llm_response(
                    system=system_prompt,
                    message=RUN_COMMAND_WITH_ERRORS_USER_PROMPT(
                        purpose=modification.purpose,
                        thinking=modification.thinking,
                        initial_command=command,
                        last_attempted_command=last_attempted_command,
                        previous_attempts=previous_errors,
                        dependencies_xml=project_dependencies.xml,
                        special_instructions_to_follow=self.task.current_workflow.context.custom_rules,
                    ),
                    response_model=NewCommandResponse,
                    model_type=Model.GEMINI_2_0_FLASH,
                )
            )
            command = new_command_response.new_command
            logger.debug(f"New command: {command}")
            command_result: InstanceExecResponse = await self.task.terminal.run_command(
                command=command
            )
            output: str = command_result.stdout
            errors: str = command_result.stderr
            last_attempted_command = AttemptedCommandResponse(
                attempted_command=command,
                agent_thinking=new_command_response.thinking,
                output=output,
                errors=errors,
            )

            previous_errors.append(last_attempted_command)

            error_classification: ErrorClassification = await _classify_errors(
                command, output, errors
            )
            did_error = error_classification.command_is_not_as_intended
            logger.debug(f"Error classification: {error_classification}")

        if attempts >= MAX_COMMAND_ATTEMPTS:
            logger.error(f"Failed to run command after {MAX_COMMAND_ATTEMPTS} attempts")

        steps_so_far.add_step(
            MiniStepRepr(
                index=step_index,
                modification_type="run_command",
                command=command,
                purpose=modification.purpose,
            )
        )

        if any(
            keyword in command
            for keyword in [" install", "upgrade", "update", " i ", " remove", " add "]
        ):
            await self.task.website.restart()

        return step_index

    async def handle_create_file(
        self,
        modification: NewFileModification,
        step_index: int,
        system_prompt: str,
        steps_so_far: MiniStepsPerformedHistory,
        project_dependencies: ProjectDependencies,
        all_file_paths: str,
    ) -> int:
        response_generator = self._retry_llm_response(
            system=system_prompt,
            message=CREATE_FILE_USER_PROMPT(
                purpose=modification.purpose,
                description=modification.description,
                task_context=self.task.current_workflow.context.xml,
                thinking=modification.thinking,
                new_file_directory=modification.new_file_directory,
                all_file_paths=all_file_paths,
                is_scraped_site=self.task.current_workflow.is_cloning_site,
                dependencies_xml=project_dependencies.xml,
                special_instructions_to_follow=self.task.current_workflow.context.custom_rules,
            )
            + f"\n\n{generate_prompt_template(CreateFileResponse)}",
            response_model=CreateFileResponse,
            image_indices=modification.image_ids,
        )

        parsed_response: CreateFileResponse | None = None
        async for event in response_generator:
            if event["type"] == "end":
                parsed_response = event["model"]
                break
            elif event["type"] == "partial":
                parsed_response = event["model"]
                if parsed_response.new_file_path and parsed_response.file_contents:
                    await self.task.file_system.create_file(
                        parsed_response.new_file_path,
                        parsed_response.file_contents,
                    )
                    await self.task.ui_functions.show_editor_tab(
                        parsed_response.new_file_path
                    )

        if not parsed_response:
            logger.error("Failed to get valid response for create_file")
            return step_index

        steps_so_far.add_step(
            MiniStepRepr(
                index=step_index,
                modification_type="create_file",
                purpose=modification.purpose,
                description=modification.description,
                new_file_path=parsed_response.new_file_path,
            )
        )

        await self.task.file_system.create_file(
            parsed_response.new_file_path, parsed_response.file_contents
        )
        await self.task.ui_functions.show_workspace_tab()

        return step_index

    async def handle_delete_file(
        self,
        modification: DeleteFileModification,
        step_index: int,
        project_dependencies: ProjectDependencies,
    ) -> int:
        await self.task.file_system.delete_file(modification.file_path)
        return step_index

    async def handle_edit_file(
        self,
        modification: ExistingFileModification,
        step_index: int,
        system_prompt: str,
        steps_so_far: MiniStepsPerformedHistory,
        project_dependencies: ProjectDependencies,
        all_file_paths: str,
    ) -> int:
        file_path: str = str(modification.file_path)
        file_object: FileObject = await self.task.file_system.get_file(file_path)
        file_contents: str = file_object.content

        response_generator = self._retry_llm_response(
            system=system_prompt,
            message=EDIT_FILE_USER_PROMPT(
                purpose=modification.purpose,
                description=modification.description,
                thinking=modification.thinking,
                task_context=self.task.current_workflow.context.xml,
                where_to_add=modification.where_to_add,
                current_file_path=file_path,
                file_contents=file_contents,
                all_file_paths=all_file_paths,
                needs_search=modification.needs_search,
                is_scraped_site=self.task.current_workflow.is_cloning_site,
                dependencies_xml=project_dependencies.xml,
                special_instructions_to_follow=self.task.current_workflow.context.custom_rules,
            )
            + f"\n\n{generate_prompt_template(EditFileResponse)}",
            original_file=file_contents,
            response_model=EditFileResponse,
            image_indices=modification.image_ids,
        )

        parsed_response: EditFileResponse | None = None
        async for event in response_generator:
            if event["type"] == "end":
                parsed_response = event["model"]
                break
            elif event["type"] == "partial":
                parsed_response = event["model"]
                for edit in parsed_response.edits:
                    if hasattr(edit, "file_contents"):
                        await self.task.ui_functions.show_editor_tab(file_path)
                        await self.task.file_system.modify_file(
                            file_path, edit.file_contents, save_to_file=False
                        )
                    elif hasattr(edit, "original_code_section") and hasattr(
                        edit, "new_code_section"
                    ):
                        new_file_contents: str | None = await merge_changes(
                            file_contents, parsed_response
                        )
                        if new_file_contents:
                            await self.task.ui_functions.show_editor_tab(file_path)
                            await self.task.file_system.modify_file(
                                file_path, new_file_contents, save_to_file=False
                            )

        if not parsed_response:
            logger.error("Failed to get valid response for edit_file")
            return step_index

        steps_so_far.add_step(
            MiniStepRepr(
                index=step_index,
                modification_type="edit_file",
                purpose=modification.purpose,
                description=modification.description,
                file_path=file_path,
            )
        )

        new_file_contents: str | None = await merge_changes(
            file_contents, parsed_response
        )
        if new_file_contents:
            await self.task.file_system.modify_file(file_path, new_file_contents)

        await self.task.ui_functions.show_workspace_tab()

        # Inject the next step
        if parsed_response.follow_up_step:
            inputs_xml: str = ""
            if "</inputs>" in system_prompt:
                inputs_xml = system_prompt.split("<inputs>")[1].split("</inputs>")[0]

            steps_to_perform: list[
                ExistingFileModification
                | NewFileModification
                | TerminalCommandModification
                | CannotFullfillStep
                | RestartWebsite
            ] = await self._handle_injected_step(
                parsed_response,
                parsed_response.follow_up_step,
                inputs_xml,
                all_file_paths,
            )
            for step in steps_to_perform:
                if isinstance(step, RestartWebsite):
                    await self.task.website.restart()
                    continue

                if isinstance(step, CannotFullfillStep):
                    logger.warning(f"Cannot fullfill step: {step}")
                    continue

                logger.debug(f"Performing injected step: {step}")

                await self.implementer_agent.perform_mini_step(
                    step,
                    system_prompt,
                    step_index,
                    steps_so_far,
                    all_file_paths,
                )

        return step_index

    async def _handle_injected_step(
        self,
        current_step: ExistingFileModification | NewFileModification,
        injected_step: FollowUpStep,
        inputs_xml: str,
        all_file_paths: str,
    ) -> list[
        ExistingFileModification
        | NewFileModification
        | TerminalCommandModification
        | RestartWebsite
        | CannotFullfillStep
    ]:
        class InjectedStepsResponse(BaseModel):
            thinking: str = Field(
                ...,
                description="Think step by step about the steps that need to be taken to complete the modification. Directly cite lines of code, functions and files where applicable to back up your thought process. Also think about how this modification fits into the big picture step and other files.",
            )
            steps: list[
                ExistingFileModification
                | NewFileModification
                | TerminalCommandModification
                | RestartWebsite
                | CannotFullfillStep
            ] = Field(
                ...,
                description="Ordered list of steps that need to be taken to complete the big picture step. A step can only perform one operation or file modification. The computer will execute the steps in order, so each step should not cause the next step to fail if performed in isolation.",
            )

        steps_response: InjectedStepsResponse = (
            await self.implementer_agent.llm_response(
                model_type=Model.CLAUDE_SONNET,
                system=INJECT_SYSTEM_PROMPT(),
                message=INJECT_USER_PROMPT(
                    current_step=current_step,
                    injected_step=injected_step,
                    inputs_xml=inputs_xml,
                    all_file_paths=all_file_paths,
                ),
                response_model=InjectedStepsResponse,
            )
        )
        return steps_response.steps

    async def _retry_llm_response(
        self,
        system: str,
        message: str,
        response_model: Type[BaseModel],
        max_retries: int = 2,
        original_file: str | None = None,
        image_indices: list[int] = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        messages: str | list[dict] = message
        if image_indices:
            messages = [
                {
                    "type": "text",
                    "text": "We have images we can use as context to fulfill this task. They are below.",
                }
            ]
            for idx in image_indices:
                if idx >= len(self.task.current_workflow.context.images):
                    logger.critical(f"Image IDX {idx} not found in images")
                    logger.critical(
                        f"Images length: {len(self.task.current_workflow.context.images)}"
                    )
                    continue

                image: Image = self.task.current_workflow.context.images[idx]
                messages.extend(image.openai_dict_format(idx))
                # ) # TODO: Benchmark openai vs anthropic for this

            messages.append({"type": "text", "text": message})

        for attempt in range(max_retries):
            response_text: str | None = None
            response_generator: AsyncGenerator[PartialStream | EndStream, None] = None
            if image_indices:
                response_generator = await self.implementer_agent.llm_response(
                    model_type=Model.GPT_4o,
                    system=system,
                    message=[{"role": "user", "content": messages}],
                    response_model=str,
                    stream=True,
                    temperature=0.2,
                )
            elif original_file:
                response_generator = await self.implementer_agent.llm_response(
                    model_type=Model.GPT_4o,
                    system=system,
                    message=[{"role": "user", "content": messages}],
                    response_model=str,
                    stream=True,
                    prediction=({"type": "content", "content": original_file}),
                    temperature=0.2,
                )
            else:
                response_generator = await self.implementer_agent.llm_response(
                    model_type=Model.CLAUDE_SONNET,
                    system=system,
                    message=[{"role": "user", "content": messages}],
                    response_model=str,
                    stream=True,
                    temperature=0.2,
                )

            async for event in response_generator:
                if isinstance(event, EndStream):
                    response_text = event.text
                    break
                elif isinstance(event, PartialStream):
                    try:
                        partial_parsed_response: response_model = parse_xml(
                            event.total_text, response_model
                        )
                        yield {"type": "partial", "model": partial_parsed_response}
                    except Exception as e:
                        logger.warning(f"Failed to parse partial response: {e}")
                        logger.warning(traceback.format_exc())
                        continue

            if response_text is None:
                logger.warning(
                    f"Attempt {attempt + 1} failed - no response text received"
                )
                continue

            try:
                parsed_response: response_model = parse_xml(
                    response_text, response_model
                )
                if not isinstance(parsed_response, response_model):
                    logger.warning(
                        f"Parsed response is not an instance of {response_model}, is actually {parsed_response}"
                    )
                    raise ValueError(
                        f"Parsed response is not an instance of {response_model}, is actually {parsed_response}"
                    )
                yield {"type": "end", "model": parsed_response}
                return
            except Exception as e:
                logger.warning(f"Failed to parse response: {e}")
                logger.warning(traceback.format_exc())
                if DEV:
                    uuid_str: str = str(uuid.uuid4())
                    with open(f"response_text_{uuid_str}.txt", "w") as f:
                        f.write(response_text)

                if attempt + 1 < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying...")
                continue

        logger.error(f"Failed to get valid response after {max_retries} attempts")
