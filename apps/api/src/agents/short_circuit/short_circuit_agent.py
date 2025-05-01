from typing import TYPE_CHECKING

from src.agents.utils.base_agent import BaseAgent
from src.prompts import (
    DATA_GEN_PROMPT_SYSTEM,
    DATA_GEN_PROMPT_USER,
    SELECTION_CONTEXT_PROMPT_SYSTEM,
    SELECTION_CONTEXT_PROMPT_USER,
)
from src.schemas.core.common import (
    ActionToPerform,
    ExistingFileModification,
    FileObject,
    GroupedSteps,
    ModificationsPlan,
    ShortCircuitAction,
)
from src.schemas.core.short_circuit import ImplementData, SelectionContextResult
from src.schemas.llm import Model

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class ShortCircuitAgent(BaseAgent):
    """
    Responsible for shortcircuiting the context and modification agents,
    especially if the user has selected components
    """

    def __init__(self, task: "Task"):
        super().__init__(task)

    async def get_action_to_perform(
        self,
        query_message: str,
    ) -> tuple[ActionToPerform, ModificationsPlan]:
        """Determine the action to perform based on the query and selected components."""
        if not self._should_process_selected_components():
            return self._create_search_action()

        change_xml: str = self._build_change_xml(query_message)
        selection_result: SelectionContextResult = await self._get_selection_context(
            change_xml
        )

        if selection_result.action_to_perform != ActionToPerform.IMPLEMENT:
            return ShortCircuitAction(
                action=selection_result.action_to_perform,
                modifications_plan=None,
                ask_clarifying_questions=selection_result.ask_clarifying_questions,
            )

        mod_plan = await self._create_modification_plan(query_message, selection_result)
        return ShortCircuitAction(
            action=selection_result.action_to_perform,
            modifications_plan=mod_plan,
            ask_clarifying_questions=selection_result.ask_clarifying_questions,
        )

    def _should_process_selected_components(self) -> bool:
        """Check if we have valid selected components to process."""
        selected = self.task.current_workflow.context.selected_components
        return (
            selected.has_selected_components and not selected.has_ambiguous_components
        )

    def _create_search_action(self) -> ShortCircuitAction:
        """Create a search action when we can't process selected components."""
        return ShortCircuitAction(
            action=ActionToPerform.SEARCH,
            modifications_plan=None,
            ask_clarifying_questions=True,
        )

    def _build_change_xml(self, query_message: str) -> str:
        """Build XML structure for the requested changes."""
        components = (
            self.task.current_workflow.context.selected_components.selected_components
        )

        change_xml = (
            f"\t<main_requested_change>{query_message}</main_requested_change>\n"
        )
        for component in components:
            change_xml += component.requested_change_xml
        return change_xml

    async def _get_selection_context(self, change_xml: str) -> SelectionContextResult:
        """Get the selection context from LLM."""
        return await self.llm_response(
            model_type=Model.CLAUDE_SONNET,
            system=SELECTION_CONTEXT_PROMPT_SYSTEM,
            message=SELECTION_CONTEXT_PROMPT_USER.format(
                user_questions="",
                requested_changes=change_xml,
            ),
            response_model=SelectionContextResult,
        )

    async def _create_modification_plan(
        self, query_message: str, selection_result: SelectionContextResult
    ) -> ModificationsPlan:
        """Create a modification plan for the selected components."""
        steps: list[ExistingFileModification] = await self._generate_modification_steps(
            query_message
        )

        return ModificationsPlan(
            thinking="",
            draft_big_picture_steps=[],
            short_analysis="",
            refined_steps=[
                GroupedSteps(
                    big_picture_step="Implement changes in selected components",
                    thinking="I just need to edit the files in the selected components and make sure the code still compiles without errors.",
                    steps=steps,
                    search_query=None,
                )
            ],
            tagline=f"Implemented {len(steps)} changes to the selected components",
            summary=selection_result.reasoning,
        )

    async def _generate_modification_steps(
        self, query_message: str
    ) -> list[ExistingFileModification]:
        steps: list[ExistingFileModification] = []
        for (
            component
        ) in self.task.current_workflow.context.selected_components.selected_components:
            file: FileObject = await self.task.file_system.get_file(component.file_path)
            component_within_file: str = self.extract_component(
                file.content, component.line_number, component.name
            )

            implement_data: ImplementData = await self.llm_response(
                model_type=Model.GPT_4o,
                system=DATA_GEN_PROMPT_SYSTEM,
                message=DATA_GEN_PROMPT_USER.format(
                    change_message=component.change_message,
                    file_path=component.file_path,
                    selected_component_code=component_within_file,
                    file_content=file.content,
                    query_message=query_message,
                ),
                response_model=ImplementData,
            )

            where_to_add: str = (
                f"""
            Do NOT change any code outside of the component unless urgently needed for the change.
            Here is the exact selected component:
            <component>
                {component_within_file}
            </component>
            """.strip()
            )

            steps.append(
                ExistingFileModification(
                    modification_type="edit_file",
                    purpose=implement_data.purpose,
                    thinking="All the changes are self-contained in this file. I can implement the requested changes",
                    file_path=component.file_path,
                    where_to_add=where_to_add,
                    api_request_ids=[],  # TODO: ADD SUPPORT FOR THIS
                    image_ids=[],  # TODO: ADD SUPPORT FOR THIS
                    description=implement_data.description,
                    needs_search=False,
                )
            )

        return steps

    def extract_component(
        self, file_content: str, start_line: int, component_name: str
    ) -> str:
        lines: list[str] = file_content.split("\n")
        component_lines: list[str] = []
        same_component_names_found: int = 0

        def is_line_commented(query: str, line: str) -> bool:
            index_of_comment_tag: int = line.find("//")
            if index_of_comment_tag == -1:
                return False

            index_of_component_name: int = line.find(query)
            return index_of_comment_tag < index_of_component_name

        for _i, line in enumerate(lines[start_line - 1 :], start=start_line):
            component_lines.append(line)

            if is_line_commented(f"<{component_name}", line):
                continue
            if is_line_commented(f"</{component_name}", line):
                continue

            if f"<{component_name}" in line:
                same_component_names_found += 1

            if f"</{component_name}" in line:
                same_component_names_found -= 1
                if same_component_names_found == 0:
                    break

        return "\n".join(component_lines)
