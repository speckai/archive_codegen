import time
import traceback
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from src.agents.implementer.modification_handler import ModificationHandler
from src.agents.utils.base_agent import BaseAgent
from src.agents.utils.debug.decorators import debug_agent_function
from src.prompts import MODIFICATION_PROMPT_SYSTEM
from src.schemas.core.common import (
    ExistingFileModification,
    FileObject,
    FileSearchResult,
    GroupedSteps,
    MessageType,
    ModificationsPlan,
    NewFileModification,
    ProjectDependencies,
    TerminalCommandModification,
)
from src.schemas.core.common.modifications import DeleteFileModification
from src.schemas.core.implementer import (
    FinishedGroupStep,
    GroupedStepsPerformedHistory,
    MiniStepsPerformedHistory,
)
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class ImplementerAgent(BaseAgent):
    def __init__(self, task: "Task"):
        super().__init__(task)
        self.task: "Task" = task
        self.modification_handler: ModificationHandler = ModificationHandler(task, self)

    @debug_agent_function
    async def implement_plan(
        self,
        modifications_plan: ModificationsPlan,
        override_files: list[FileObject] = None,
    ) -> ModificationsPlan:
        """Implement the given modifications plan. Perform each step and send updates."""
        grouped_steps: GroupedSteps = modifications_plan.refined_steps
        start_time = time.time()
        performed_groups_so_far: GroupedStepsPerformedHistory = (
            GroupedStepsPerformedHistory(steps=[])
        )

        for step_idx, step in enumerate(grouped_steps):
            async for change_idx in self.task.implementer.perform_big_step(
                step,
                performed_groups_so_far,
                override_files,
            ):
                await self.send_update_data(
                    MessageType.MODIFICATION_PERFORMED,
                    {
                        "group": step_idx,
                        "step": change_idx,
                    },
                )
                logger.info(
                    f"Step {step_idx}-{change_idx} performed in {time.time() - start_time} seconds"
                )
                start_time = time.time()
                performed_groups_so_far.add_step(
                    FinishedGroupStep(
                        idx=step_idx,
                        big_step=step,
                        mini_steps_performed=MiniStepsPerformedHistory(steps=[]),
                    )
                )
        return modifications_plan

    async def perform_big_step(
        self,
        big_step: GroupedSteps,
        performed_groups_so_far: GroupedStepsPerformedHistory,
        override_files: list[FileObject] = None,
    ) -> AsyncGenerator[int]:
        """Perform a big single grouped step within a ModificationsPlan"""
        search_results_xml: str = await self._get_search_results(
            big_step, override_files
        )
        all_file_paths: str = (
            await self.task.file_system.get_all_tracked_file_path_trees()
        )  # TODO: benchmark vs get_all_tracked_file_paths()

        mini_steps_so_far: MiniStepsPerformedHistory = MiniStepsPerformedHistory(
            steps=[]
        )

        for small_step_index, modification in enumerate(big_step.steps):
            system_prompt: str = MODIFICATION_PROMPT_SYSTEM(
                overall_summary=big_step.big_picture_step,
                previous_steps_in_group=mini_steps_so_far.xml,
                next_steps_in_group=big_step.get_steps_starting_from_idx(
                    start_idx=small_step_index
                ),
                previous_groups_in_plan="\n".join(
                    [step.xml for step in performed_groups_so_far.steps]
                ),
                file_search_results=search_results_xml,
                needs_search=True,
                # needs_search=modification.needs_search, # TODO: Fix this
            )
            try:
                yield await self.perform_mini_step(
                    modification,
                    system_prompt,
                    small_step_index,
                    mini_steps_so_far,
                    all_file_paths,
                )
            except Exception as e:
                logger.error(e)
                logger.error(traceback.format_exc())
                with open("error_modification.json", "w") as f:
                    f.write(modification.model_dump_json())

        # logger.warning(f"Modified urls: {big_step.modified_urls}")
        # await self.task.website.perform_runtime_test(big_step.modified_urls)
        # If the runtime test fails, we need to figure out if we should fix the error

    async def perform_mini_step(
        self,
        modification: (
            TerminalCommandModification
            | NewFileModification
            | ExistingFileModification
            | DeleteFileModification
        ),
        system_prompt: str,
        small_step_index: int,
        mini_steps_so_far: MiniStepsPerformedHistory,
        all_file_paths: str = None,
    ) -> int:
        if not all_file_paths:
            all_file_paths = (
                await self.task.file_system.get_all_tracked_file_path_trees()
            )

        project_dependencies: ProjectDependencies = (
            await self.task.file_system.get_dependencies()
        )

        if isinstance(modification, TerminalCommandModification):
            return await self.modification_handler.handle_run_command(
                modification,
                small_step_index,
                system_prompt,
                mini_steps_so_far,
                project_dependencies,
            )
        elif isinstance(modification, NewFileModification):
            return await self.modification_handler.handle_create_file(
                modification,
                small_step_index,
                system_prompt,
                mini_steps_so_far,
                project_dependencies,
                all_file_paths,
            )
        elif isinstance(modification, ExistingFileModification):
            return await self.modification_handler.handle_edit_file(
                modification,
                small_step_index,
                system_prompt,
                mini_steps_so_far,
                project_dependencies,
                all_file_paths,
            )
        elif isinstance(modification, DeleteFileModification):
            return await self.modification_handler.handle_delete_file(
                modification,
                small_step_index,
                project_dependencies,
            )

    async def _get_search_results(
        self, big_step: GroupedSteps, override_files: list[FileObject]
    ) -> str:
        search_query: str = big_step.search_query
        if not search_query or search_query.lower().startswith("none"):
            return ""

        search_results: list[FileSearchResult] = (
            await self.task.search_agent.search_codebase(
                f"Search query: {search_query}\nStep: {big_step.big_picture_step}",
                override_files=override_files,
            )
        )

        return "\n".join(result.xml for result in search_results)
