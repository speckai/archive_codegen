from typing import Literal, Union

from pydantic import BaseModel, Field


class CodeModification(BaseModel):
    original_code: str = Field(
        None,
        description="Original code snippet, copied exactly from the file",
    )
    modified_code: str = Field(
        None,
        description="Modified code snippet with the implemented changes",
    )


class PerformCodeModification(BaseModel):
    thinking: str = Field(
        None,
        description="Concisely describe the changes that need to be made to address the error",
    )
    modifications: list[CodeModification] = Field(
        None, description="List of modifications to make to the file"
    )


class InspectAndModifyFile(BaseModel):
    file_path: str = Field(
        None, description="Path to the file that needs to be modified"
    )


class InspectFile(BaseModel):
    id: Literal["inspect_file"] = "inspect_file"
    file_path: str = Field(
        None, description="Path to the file that needs to be inspected"
    )


class SemanticSearch(BaseModel):
    id: Literal["semantic_search"] = "semantic_search"
    query: str = Field(None, description="Query to search for in the codebase")


class Search(BaseModel):
    id: Literal["search"] = "search"
    query: str = Field(None, description="Query to search for in the codebase")


class RunCommand(BaseModel):
    id: Literal["run_command"] = "run_command"
    command: str = Field(
        None,
        description="Command to run in the terminal. If using a package manager, use the package manager specified in the package_manager field.",
    )


class DebugResponse(BaseModel):
    extracted_error: str = Field(
        ..., description="What error/errors are breaking the build?"
    )
    concise_thoughts: str = Field(
        ..., description="Concise thoughts on the error and how to fix it"
    )
    your_solution: str = Field(..., description="What is your solution to the error?")
    actions: list[
        Union[
            InspectAndModifyFile,
            InspectFile,
            SemanticSearch,
            Search,
            RunCommand,
        ]
    ] = Field(
        ...,
        description="Fewest actions to take to debug the extracted_error. You are required to include either a InspectAndModifyFile or RunCommand action at the end. Prefer to take actions that are unlikely to break the code.",
    )
