from typing import Literal, Union

from pydantic import BaseModel, Field
from src.schemas.core.common.modifications import GroupedSteps
from src.utils.prompt_utils import format_prompt


class SectionEdit(BaseModel):
    original_code_section: str = Field(..., description="The original code section")
    new_code_section: str = Field(..., description="The new code section")

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <section_edit>
        <original_code_section>{self.original_code_section}</original_code_section>
        <new_code_section>{self.new_code_section}</new_code_section>
        </section_edit>
        """)


class FullFileContents(BaseModel):
    file_contents: str = Field(..., description="The full file contents to edit")

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <full_file_contents>
        {self.file_contents}
        </full_file_contents>
        """)


class CannotFullfillStep(BaseModel):
    reasoning: str = Field(
        ..., description="Concise reasoning for why the step cannot be fulfilled"
    )


class FollowUpStep(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    step_to_perform: str = Field(..., description="The step to perform. ")

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <follow_up_step>
        <thinking>{self.thinking}</thinking>
        <step_to_perform>{self.step_to_perform}</step_to_perform>
        </follow_up_step>
        """)


class RunCommandResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    command: str = Field(..., description="The final command")


class CreateFileResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    new_file_path: str = Field(..., description="The path to the new file")
    file_contents: str = Field(..., description="The full updated file contents")
    follow_up_step: Union[FollowUpStep, None] = Field(
        None,
        description="A follow up step to perform after this step ONLY if needed. This is only if we need to perform a follow up step and it isn't already in the step plan.",
    )

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <create_file_response>
        <thinking>{self.thinking}</thinking>
        <new_file_path>{self.new_file_path}</new_file_path>
        <file_contents>{self.file_contents}</file_contents>
        <follow_up_step>{self.follow_up_step.xml}</follow_up_step>
        </create_file_response>
        """)


class DeleteFileResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    file_path: str = Field(..., description="The path to the file to delete")
    follow_up_step: Union[FollowUpStep, None] = Field(
        None,
        description="A follow up step to perform after this step ONLY if needed. This is only if we need to perform a follow up step and it isn't already in the step plan.",
    )

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <delete_file_response>
        <thinking>{self.thinking}</thinking>
        <file_path>{self.file_path}</file_path>
        <follow_up_step>{self.follow_up_step.xml}</follow_up_step>
        </delete_file_response>
        """)


class EditFileResponse(BaseModel):
    thinking: str = Field(..., description="The thinking to perform")
    num_sections_to_modify: int = Field(
        ..., description="The number of sections to modify"
    )
    edits: list[Union[SectionEdit, FullFileContents]] = Field(
        ..., description="The inline_edits to make to the file"
    )
    follow_up_step: Union[FollowUpStep, None] = Field(
        None,
        description="A follow up step to perform after this step ONLY if needed. This is only if we need to perform a follow up step and it isn't already in the step plan.",
    )

    @property
    def xml(self) -> str:
        return format_prompt(f"""
        <edit_file_response>
        <thinking>{self.thinking}</thinking>
        <num_sections_to_modify>{self.num_sections_to_modify}</num_sections_to_modify>
        <edits>{"\n".join([edit.xml for edit in self.edits])}</edits>
        <follow_up_step>{self.follow_up_step.xml}</follow_up_step>
        </edit_file_response>
        """)


class CreatedSteps(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    steps: list[EditFileResponse | CreateFileResponse] = Field(
        ..., description="The steps to perform to fulfill the request"
    )


class MiniStepRepr(BaseModel):
    index: int
    modification_type: Literal["run_command", "create_file", "edit_file", "delete_file"]
    purpose: str
    command: str | None = None  # For run_command
    description: str | None = None  # For edit_file and create_file
    new_file_path: str | None = None  # For create_file
    file_path: str | None = None  # For edit_file

    @property
    def xml(self) -> str:
        optional_fields = [
            f"<command>{self.command}</command>" if self.command else "",
            f"<description>{self.description}</description>"
            if self.description
            else "",
            f"<new_file_path>{self.new_file_path}</new_file_path>"
            if self.new_file_path
            else "",
            f"<file_path>{self.file_path}</file_path>" if self.file_path else "",
        ]
        return "\n".join(
            filter(
                None,
                [
                    f"<step_{self.index}>",
                    f"<modification_type>{self.modification_type}</modification_type>",
                    f"<purpose>{self.purpose}</purpose>",
                    *optional_fields,
                    f"</step_{self.index}>",
                ],
            )
        )


class MiniStepsPerformedHistory(BaseModel):
    steps: list[MiniStepRepr]

    @property
    def xml(self) -> str:
        return format_prompt(f"""
<steps_performed>
{"\n".join([step.xml for step in self.steps])}
</steps_performed>
""")

    def add_step(self, step: MiniStepRepr) -> None:
        self.steps.append(step)


class FinishedGroupStep(BaseModel):
    idx: int
    big_step: GroupedSteps
    mini_steps_performed: MiniStepsPerformedHistory

    @property
    def xml(self) -> str:
        return format_prompt(f"""
            <grouped_step_{self.idx}>
            <purpose>{self.big_step.big_picture_step}</purpose>
            <planner_thought_process>{self.big_step.thinking}</planner_thought_process>
            <mini_steps_performed>
            {self.mini_steps_performed.xml}
            </mini_steps_performed>
            </grouped_step_{self.idx}>
            """)


class GroupedStepsPerformedHistory(BaseModel):
    steps: list[FinishedGroupStep]

    def add_step(self, step: FinishedGroupStep) -> None:
        self.steps.append(step)


class AttemptedCommandResponse(BaseModel):
    attempted_command: str
    agent_thinking: str
    output: str
    errors: str

    @property
    def xml(self):
        return f"""
<attempted_command>
{self.attempted_command}
</attempted_command>
<agent_thinking>
{self.agent_thinking}
</agent_thinking>
<stdout>
{self.output}
</stdout>
<stderr>
{self.errors}
</stderr>
"""

    def xml_with_index(self, index: int):
        return f"""
<attempt_{index}>
<attempted_command>
{self.attempted_command}
</attempted_command>
<agent_thinking>
{self.agent_thinking}
</agent_thinking>
<stdout>
{self.output}
</stdout>
<stderr>
{self.errors}
</stderr>
</attempt_{index}>
"""


class ErrorClassification(BaseModel):
    thinking: str = Field(..., description="Space for deep thinking on the error")
    command_is_not_as_intended: bool = Field(
        ...,
        description="Whether the command did not work as intended and if we should think and try a different command",
    )


class NewCommandResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    new_command: str = Field(..., description="The new command to try")
