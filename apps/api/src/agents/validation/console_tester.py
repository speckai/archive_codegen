from typing import TYPE_CHECKING

from morphcloud.api import InstanceExecResponse
from src.agents.utils.debug.decorators import debug_agent_function
from src.prompts.validation.build_debug import (
    GET_FIX_ACTION_SYSTEM_PROMPT,
    GET_FIX_ACTION_USER_PROMPT,
    IMPLEMENTER_STEP_SYSTEM_PROMPT,
)
from src.schemas.core.common import (
    ChatMessageRole,
    DeleteFileModification,
    ExistingFileModification,
    FileObject,
    MainMessage,
    MessageData,
    MessageType,
    NewFileModification,
    ProjectDependencies,
    RestartWebsite,
    TerminalCommandModification,
)
from src.schemas.core.implementer import MiniStepRepr, MiniStepsPerformedHistory
from src.schemas.core.validation import (
    DebugPlan,
    DoNothing,
    FixAction,
    GetFileContents,
    RequestedCommandOutput,
    RequestedFileContents,
    RunCommand,
    RuntimeResult,
    TestPlan,
)
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task
    from src.agents.validation.validation_agent import ValidationAgent

MAX_ITERATIONS: int = 15


class ConsoleTester:
    def __init__(
        self,
        task: "Task",
        agent: "ValidationAgent",
    ):
        self.task = task
        self.agent = agent

        self.performed_actions: list[FixAction] = (
            []
        )  # Actions that the agent used to collect context or break the loop
        self.previous_contexts: list[RequestedCommandOutput | RequestedFileContents] = (
            []
        )  # Context that the agent collected
        self.previous_plan_attempts: list[DebugPlan] = (
            []
        )  # DebugPlans that the agent tried
        self.dev_command: str = ""
        self.last_runtime_results: list[RuntimeResult] = []

    async def perform_console_log_test(self, test_plan: TestPlan) -> bool:
        self.dev_command = await self.task.settings.get_dev_command()
        self.performed_actions = []
        self.previous_contexts = []
        self.previous_plan_attempts = []

        did_send_chat: bool = False

        while len(self.performed_actions) < MAX_ITERATIONS:
            runtime_results: list[RuntimeResult] = (
                await self.task.website.perform_runtime_test(
                    urls=test_plan.urls_to_test
                )
            )
            self.last_runtime_results = runtime_results

            contains_errors: list[bool] = [
                any(result.stderr)
                or any("error" in line.lower() for line in result.stdout)
                for result in runtime_results
            ]

            if not any(contains_errors):  # No errors found
                logger.info("ValidationAgent: No errors found")
                return True

            runtime_url_tested_errors: list[str] = self._get_non_duplicated_errors_xml(
                runtime_results
            )

            file_paths: str = (
                await self.task.file_system.get_all_tracked_file_path_trees()
            )
            project_dependencies: ProjectDependencies = (
                await self.task.file_system.get_dependencies()
            )

            await self.task.send_update_data(MessageType.DETERMINING_NEXT_STEP, {})
            action: FixAction = await self.agent.llm_response(
                model_type=Model.CLAUDE_SONNET,
                system=GET_FIX_ACTION_SYSTEM_PROMPT(len(self.performed_actions)),
                message=GET_FIX_ACTION_USER_PROMPT(
                    dev_command=self.dev_command,
                    task_context=self.task.current_workflow.context.xml,
                    extracted_errors=runtime_url_tested_errors,
                    file_paths=file_paths,
                    dependencies_xml=project_dependencies.xml,
                    previous_contexts=self.previous_contexts,
                    performed_actions=self.performed_actions,
                ),
                response_model=FixAction,
            )

            if isinstance(action.action, DoNothing):
                logger.info("ValidationAgent: No action taken")
                return True

            if not did_send_chat:
                await self.task.chat.add_message(
                    ChatMessageRole.ASSISTANT,
                    MessageData(
                        main_message=MainMessage(
                            message="I've found some errors. I'm going to fix them."
                        )
                    ),
                )
                did_send_chat = True

            elif isinstance(action.action, RunCommand):
                await self.task.send_update_data(
                    MessageType.COLLECTING_CONTEXT,
                    {
                        "purpose": action.action.purpose,
                        "type": "command",
                        "content": action.action.command,
                    },
                )
                result: InstanceExecResponse = await self.task.terminal.run_command(
                    action.action.command
                )
                logger.debug(
                    f"ValidationAgent: Running command: {action.action.command}"
                )

                self.previous_contexts.append(
                    RequestedCommandOutput(
                        command=action.action.command,
                        output=result.stdout,
                        errors=result.stderr,
                        status_code=result.exit_code,
                    )
                )

            elif isinstance(action.action, GetFileContents):
                await self.task.send_update_data(
                    MessageType.COLLECTING_CONTEXT,
                    {
                        "purpose": action.action.purpose,
                        "type": "file",
                        "content": action.action.file_path,
                    },
                )
                file_object: FileObject = await self.task.file_system.get_file(
                    action.action.file_path
                )
                self.previous_contexts.append(
                    RequestedFileContents(
                        file_path=action.action.file_path, contents=file_object.content
                    )
                )

            elif isinstance(action.action, DebugPlan):
                await self.task.send_update_data(
                    MessageType.ATTEMPTING_FIX,
                    {
                        "thinking": action.thinking,
                        "actions": [
                            mini_action.pruned_context()
                            for mini_action in action.action.steps
                        ],
                    },
                )
                await self._perform_debug_plan(action.action)

            self.performed_actions.append(action)
            await self.task.send_update_data(
                MessageType.ACTION_HISTORY,
                {
                    "actions": [
                        action.pruned_context() for action in self.performed_actions
                    ],
                },
            )

    def _get_non_duplicated_errors_xml(
        self, runtime_results: list[RuntimeResult]
    ) -> list[str]:
        runtime_url_tested_errors: list[str] = []
        non_duplicated_errors: list[str] = []
        for result in runtime_results:
            non_duplicated_errors: list[str] = []
            for error in result.stderr:
                if error not in non_duplicated_errors:
                    non_duplicated_errors.append(error)
            non_duplicated_errors.extend(
                line for line in result.stdout if "error" in line.lower()
            )
            if non_duplicated_errors:
                result.stderr = non_duplicated_errors
                runtime_url_tested_errors.append(
                    result.xml_error(len(runtime_url_tested_errors) + 1)
                )
        return runtime_url_tested_errors

    @debug_agent_function
    async def _perform_debug_plan(self, plan: DebugPlan) -> None:
        plan_steps_so_far: MiniStepsPerformedHistory = MiniStepsPerformedHistory(
            steps=[]
        )  # Steps that the agent has performed this iteration
        for idx, step in enumerate(plan.steps):
            await self.task.send_update_data(
                MessageType.DEBUG_STEP_PERFORMED,
                {
                    "index": idx,
                },
            )

            if isinstance(step, RestartWebsite):
                await self.task.website.restart()
            else:
                _step_result: int = await self.task.implementer.perform_mini_step(
                    modification=step,
                    system_prompt=IMPLEMENTER_STEP_SYSTEM_PROMPT(
                        command=self.dev_command,
                        previous_plan_attempts=self.previous_plan_attempts,
                        previous_contexts=self.previous_contexts,
                    ),
                    small_step_index=0,
                    mini_steps_so_far=plan_steps_so_far,
                )

                to_add: MiniStepRepr
                if isinstance(step, NewFileModification):
                    to_add = MiniStepRepr(
                        index=len(plan_steps_so_far.steps),
                        modification_type="create_file",
                        file_path=step.new_file_directory,
                        purpose=step.purpose,
                    )
                elif isinstance(step, ExistingFileModification):
                    to_add = MiniStepRepr(
                        index=len(plan_steps_so_far.steps),
                        modification_type="edit_file",
                        file_path=step.file_path,
                        purpose=step.purpose,
                    )
                elif isinstance(step, TerminalCommandModification):
                    to_add = MiniStepRepr(
                        index=len(plan_steps_so_far.steps),
                        modification_type="run_command",
                        command=step.command,
                        purpose=step.purpose,
                    )
                elif isinstance(step, DeleteFileModification):
                    to_add = MiniStepRepr(
                        index=len(plan_steps_so_far.steps),
                        modification_type="delete_file",
                        file_path=step.file_path,
                        purpose=step.purpose,
                    )
                else:
                    raise ValueError(f"Unknown step type: {type(step)}")

                plan_steps_so_far.add_step(to_add)

        self.previous_plan_attempts.append(plan)
