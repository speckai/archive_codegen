from typing import Literal

from pydantic import BaseModel, Field
from src.schemas.core.common.modifications import (
    DeleteFileModification,
    ExistingFileModification,
    NewFileModification,
    RestartWebsite,
    TerminalCommandModification,
)


class DebugPlan(BaseModel):
    thinking: str = Field(
        ...,
        description="Thoughts about the error and the steps to fix it.",
    )
    purpose: str = Field(..., description="The purpose of the debug plan")
    steps: list[
        ExistingFileModification
        | NewFileModification
        | TerminalCommandModification
        | DeleteFileModification
        | RestartWebsite
    ] = Field(
        ...,
        description="Steps to fix the error.",
    )

    def xml_with_index(self, index: int) -> str:
        return f"""
<debug_plan_attempt_{index}>
<thinking>
{self.thinking}
</thinking>
<steps>
{"\n".join([step.xml_with_index(index) for index, step in enumerate(self.steps)])}
</steps>
</debug_plan_attempt_{index}>
""".strip()


class DoNothing(BaseModel):
    id: Literal["do_nothing"] = "do_nothing"


class RunCommand(BaseModel):
    purpose: str = Field(..., description="The purpose of the command")
    command: str = Field(..., description="The command to run")

    def xml_with_index(self, index: int) -> str:
        return f"""
<action_{index}>
<type>
RunCommand
</type>
<purpose>
{self.purpose}
</purpose>
<command>
{self.command}
</command>
</action_{index}>
""".strip()


class GetFileContents(BaseModel):
    purpose: str = Field(..., description="The purpose of the file contents")
    file_path: str = Field(..., description="The file to get the contents of")

    def xml_with_index(self, index: int) -> str:
        return f"""
<action_{index}>
<type>
GetFileContents
</type>
<purpose>
{self.purpose}
</purpose>
<file_path>
{self.file_path}
</file_path>
</action_{index}>
""".strip()


class FixAction(BaseModel):
    thinking: str = Field(
        ..., description="The thinking that the agent did to fix the errors"
    )
    action: RunCommand | GetFileContents | DebugPlan | DoNothing

    def xml_with_index(self, index: int) -> str:
        return f"""
<action_{index}>
<thinking>
{self.thinking}
</thinking>
<action>
{self.action.xml_with_index(index)}
</action>
</action_{index}>
""".strip()

    def pruned_context(self) -> dict:
        action_type: str
        purpose: str
        if isinstance(self.action, RunCommand):
            action_type = "command"
            purpose = self.action.purpose
        elif isinstance(self.action, GetFileContents):
            action_type = "file"
            purpose = self.action.purpose
        elif isinstance(self.action, DebugPlan):
            action_type = "plan"
            purpose = self.action.purpose
        elif isinstance(self.action, DoNothing):
            action_type = "nothing"
            purpose = "Do nothing, this error is not needed to be fixed"

        return {
            "thinking": self.thinking,
            "purpose": purpose,
            "type": action_type,
        }


class RequestedCommandOutput(BaseModel):
    command: str = Field(..., description="The command that the agent requested")
    output: str = Field(..., description="The output of the command")
    errors: str = Field(..., description="The errors from the command")
    status_code: int = Field(..., description="The status code of the command")

    @property
    def xml(self) -> str:
        return f"""
<requested_command_output>
<command>
{self.command}
</command>
<stdout>
{self.output}
</stdout>
<stderr>
{self.errors}
</stderr>
<status_code>
{self.status_code}
</status_code>
</requested_command_output>
""".strip()


class RequestedFileContents(BaseModel):
    file_path: str = Field(..., description="The file path that the agent requested")
    contents: str = Field(..., description="The contents of the file")

    @property
    def xml(self) -> str:
        return f"""
<requested_file_contents>
<file_path>
{self.file_path}
</file_path>
<file_contents>
{self.contents}
</file_contents>
</requested_file_contents>
""".strip()
