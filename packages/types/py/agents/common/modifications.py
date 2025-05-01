from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    CREATE_FILE = "create_file"
    EDIT_FILE = "edit_file"
    RUN_COMMAND = "run_command"


class ExistingFileModification(BaseModel):
    modification_type: Literal["edit_file"]
    purpose: str = Field(
        ...,
        description="The purpose of this modification.",
    )
    thinking: str = Field(
        ...,
        description="Think step by step about the steps that need to be taken to complete the modification. Directly cite lines of code, functions and files where applicable to back up your thought process. Also think about how this modification fits into the big picture step and other files.",
    )
    file_path: str = Field(
        ...,
        description="The path to the file that needs to be modified.",
    )
    where_to_add: str = Field(
        ...,
        description="High level description of what to replace in the file, or  where to add the new code",
    )
    api_request_ids: list[int] = Field(
        ...,
        description="List of ids of the API requests that we can use for this modification.",
    )
    description: str = Field(
        ...,
        description="Comprehensive natural language instructions of what to edit in the file. Do not include any code in this field, but describe the edits in a very verbose manner.",
    )
    needs_search: bool = Field(
        ...,
        description="Evaluate if this step needs other files outside of the current file to better complete the modification.",
    )


class NewFileModification(BaseModel):
    modification_type: Literal["create_file"]
    purpose: str = Field(
        ...,
        description="The purpose of this modification.",
    )
    thinking: str = Field(
        ...,
        description="Think step by step about the steps that need to be taken to complete the modification. Directly cite lines of code, functions and files where applicable to back up your thought process. Also think about how this modification fits into the big picture step and other files.",
    )
    new_file_directory: str = Field(
        ...,
        description="The path to the directory ending with '/' where the new file needs to be created.",
    )
    api_request_ids: list[int] = Field(
        ...,
        description="List of ids of the API requests that we can use for this modification.",
    )
    description: str = Field(
        ...,
        description="Comprehensive natural language instructions of what to write in the new file. Do not include any code in this field, but describe the contents in a very verbose manner.",
    )
    needs_file_paths: bool = Field(
        ...,
        description="Evaluate if this step needs the file paths of all the files in the codebase to better complete the modification.",
    )


class TerminalCommandModification(BaseModel):
    modification_type: Literal["run_command"]
    purpose: str = Field(
        ...,
        description="The purpose of this modification.",
    )
    thinking: str = Field(
        ...,
        description="Think step by step about the command that needs to be executed and why it needs to be executed. If installing dependencies, install any possible dependencies that could be needed.",
    )
    command: str = Field(
        ...,
        description="The exact bash command that needs to be executed. If using a package manager, use the package manager specified in the package_manager field.",
    )


class GroupedSteps(BaseModel):
    big_picture_step: str = Field(
        ...,
        description="Tagline for what this big picture step is. No longer than a concise sentence.",
    )
    thinking: str = Field(
        ...,
        description="Use chain of thought reasoning to determine the steps that need to be taken to complete the big picture step. Directly cite lines of code, functions and files where applicable to back up your thought process. If using new dependencies or creating new files, think about the order of operations to ensure that dependencies are installed or created before they are implemented in the code.",
    )
    steps: list[
        Union[
            ExistingFileModification, NewFileModification, TerminalCommandModification
        ]
    ] = Field(
        ...,
        description="Ordered list of steps that need to be taken to complete the big picture step. A step can only perform one operation or file modification. The computer will execute the steps in order, so each step should not cause the next step to fail if performed in isolation.",
    )
    search_query: Union[str, None] = Field(
        ...,
        description="Search query to identify relevant code snippets for the big picture step. Include context about the step's purpose and change scope. Answer None if not needed. Max 2 sentences.",
    )


class DraftStep(BaseModel):
    thinking: str = Field(
        ...,
        description="Think step by step to think about given a set of changes, what is the next big picture step that needs to be taken. Think about how the previous steps led to this step.",
    )
    step_name: str = Field(
        ...,
        description="Name of the big picture step. No longer than 2 sentences.",
    )
    mini_steps: list[str] = Field(
        ...,
        description="Ordered list of the steps within the big picture step that need to be taken to complete the modifications. ",
    )


class ModificationsPlan(BaseModel):
    """
    Note: files.SelectionContextResult has 2 fields from here for modification shortcircuiting.
    """

    thinking: str = Field(
        ...,
        description="Think step by step using chain of thought reasoning about how you would implement the changes to the codebase. Consider all possible options and analyze how each option adheres to the modifications_rules and specific_instructions before you decide on the best way to implement the changes.",
    )
    draft_big_picture_steps: list[DraftStep] = Field(
        ...,
        description="A list of draft steps that can be used to complete the modifications. Each step should be independent and not do too much, generally confined to one sub-directory/set of files. Steps will have mini-steps that are individual steps within the big picture step to achieve the goal. No testing, run or build steps.",
    )
    short_analysis: str = Field(
        ...,
        description="Compare the draft steps to the user's request and determine what modifications need to be made to make the steps more effective at completing the user's request. Prune any steps that are not needed or add any steps that are needed. Specifically analyze how the steps adhere to the modifications_rules and specific_instructions. If anything does not adhere to these rules, explain how we can change the step to adhere to the rules and instructions.",
    )
    refined_steps: list[GroupedSteps] = Field(
        ...,
        description="Use your analysis to refine the drafted steps into the final grouped steps and implement any changes you deem necessary.",
    )
    tagline: str = Field(
        ...,
        description="Brief, friendly user oriented message acknowledging the changes and providing a brief summary of the changes to the user's request. This will be displayed to the user AFTER the plan has been implemented.",
    )
    summary: str = Field(
        ...,
        description="Concise summary of each individual change made. Each summary should start with a bullet point hyphen and be on a new line. This will be displayed to the user AFTER the plan has been implemented.",
    )
