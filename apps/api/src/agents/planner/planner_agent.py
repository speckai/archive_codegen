import time
from typing import TYPE_CHECKING

from src.agents.utils.base_agent import BaseAgent
from src.prompts import PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT
from src.schemas.core.common import (
    ActionToPerform,
    FileSearchResult,
    MessageType,
    ModificationsPlan,
    ProjectDependencies,
    ShortCircuitAction,
)
from src.utils.llm.handler import Model
from src.utils.logging import logger
from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Planner(BaseAgent):
    def __init__(self, task: "Task"):
        super().__init__(task)

    async def request_modifications_plan(
        self,
        change_prompt: str,
        short_circuit_action: ShortCircuitAction,
        file_search_results: list[FileSearchResult] = None,
    ) -> ModificationsPlan:
        """Request a modifications plan based on the change prompt and code chunks. Create and refine the plan."""
        if short_circuit_action.modifications_plan is not None:
            return await self._short_circuit_plan(
                short_circuit_action.modifications_plan
            )

        file_search_results: list[FileSearchResult] = (
            await self._get_file_search_results(
                short_circuit_action, file_search_results, change_prompt
            )
        )

        start_time = time.time()
        logger.info("Starting to write plan")
        modifications_plan: ModificationsPlan = await self._create_modifications_plan(
            change_prompt,
            file_search_results,
        )
        logger.info(f"Plan written in {time.time() - start_time} seconds")

        await self.send_update_data(
            MessageType.PLAN_GENERATED,
            {"plan": modifications_plan.model_dump()},
        )

        return modifications_plan

    async def _get_file_search_results(
        self,
        short_circuit_action: ShortCircuitAction,
        file_search_results: list[FileSearchResult],
        change_prompt: str,
    ) -> list[FileSearchResult]:
        if short_circuit_action.action == ActionToPerform.SEARCH:
            if not file_search_results:  # For overriding
                file_search_results: list[FileSearchResult] = (
                    await self.task.search_agent.search_codebase(change_prompt)
                )
                file_names: list[str] = [file.file_path for file in file_search_results]
                await self.send_update_data(
                    MessageType.FILE_SEARCH_RESULTS, {"files": file_names}
                )
        elif not file_search_results:  # Skip search, add selected components to results
            results: list[FileSearchResult] = []
            # TODO: Redo this
            file_search_results = results
        return file_search_results

    async def _short_circuit_plan(
        self, modifications_plan: ModificationsPlan
    ) -> ModificationsPlan:
        logger.info("Skipping planning")
        await self.send_update_data(
            MessageType.PLAN_GENERATED,
            {"plan": modifications_plan.model_dump()},
        )
        return modifications_plan

    async def _create_modifications_plan(
        self,
        change_prompt: str,
        file_search_results: list[FileSearchResult],
    ) -> ModificationsPlan:
        image_contents: list[dict] = self._construct_image_list()

        searched_files_xml: str = "\n".join(
            result.xml for result in file_search_results
        )
        file_paths: str = await self.task.file_system.get_all_tracked_file_path_trees()
        package_manager: str = await self.task.settings.get_package_manager()
        project_dependencies: ProjectDependencies = (
            await self.task.file_system.get_dependencies()
        )

        message_contents: list[dict[str, str]] = image_contents + [
            {
                "type": "text",
                "text": PLANNING_USER_PROMPT(
                    requested_changes=change_prompt,
                    file_paths=file_paths,
                    relevant_searched_files=searched_files_xml,
                    package_manager=package_manager,
                    relevant_chats=self.task.current_workflow.context.relevant_chats,
                    is_cloning_site=self.task.current_workflow.is_cloning_site,
                    dependencies_xml=project_dependencies.xml,
                ),
            }
        ]

        messages: list[dict[str, str]] = [
            {
                "role": "user",
                "content": message_contents,
            }
        ]

        model_type = Model.GPT_4o if image_contents else Model.CLAUDE_SONNET

        modifications_plan: ModificationsPlan = await self.llm_response(
            model_type=model_type,  # TODO: benchmark openai vs anthropic
            system=PLANNING_SYSTEM_PROMPT,
            message=messages,
            response_model=ModificationsPlan,
            # TODO: Use stream=True
        )

        return modifications_plan

    def _construct_image_list(self) -> list[dict]:
        image_contents: list[dict] = []
        if self.task.current_workflow.context.images:
            text = format_prompt(
                """
                The user has attached images for you to use while planning. \
                Each image should be a new step with steps that create the components used in the image. \
                Carefully analyze the image when creating the steps to ensure exact pixel perfect recreation.
                """
                if self.task.current_workflow.is_cloning_site
                else """
                The user has attached images for you to use while planning. \
                If any images are relevant, inject them into the steps.
                """
            )
            image_contents.append(
                {
                    "type": "text",
                    "text": text,
                }
            )

        for idx, image in enumerate(self.task.current_workflow.context.images):
            if idx == len(self.task.current_workflow.context.images) - 1:
                image_contents.append(
                    {
                        "type": "text",
                        "text": "This is the full site image. Use this ",
                    }
                )
            # image_contents.extend(image.anthropic_dict_format(idx))
            image_contents.extend(image.openai_dict_format(idx))
        return image_contents
