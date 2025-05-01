from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.schemas.core.common import ExistingFileModification, NewFileModification
    from src.schemas.core.implementer import FollowUpStep


def INJECT_SYSTEM_PROMPT() -> str:
    return format_prompt(
        """
You are an expert React engineer. You are given a list of steps to perform to fulfill a request, and have to perform the next step.
"""
    )


def INJECT_USER_PROMPT(
    current_step: "ExistingFileModification | NewFileModification",
    injected_step: "FollowUpStep",
    inputs_xml: str,
    all_file_paths: str,
) -> str:
    return format_prompt(
        f"""
You are given a list of steps to perform to fulfill a request, and have to create the next step.

{inputs_xml}

Information about the current step you are on:
{current_step.xml}

Information about the next step you should return:
{injected_step.xml}

All the git tracked files in the codebase:
<all_file_paths>
{all_file_paths}
</all_file_paths>

If the injected step wants to restart the website, you should use the RestartWebsite step.

Use the information given to you to inform the best way to perform the next step.
"""
    )
