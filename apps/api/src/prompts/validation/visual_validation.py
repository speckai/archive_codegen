from src.utils.prompt_utils import format_prompt


def VALIDATION_SYSTEM() -> str:
    return format_prompt(
        """
You are a senior QA analyst who is validating the new code a developer wrote to fulfill a user's request. You are to be strict and diligent. 
"""
    )


def VALIDATION_USER_PROMPT(test_case: str, original_bug_report: str) -> str:
    return format_prompt(
        f"""
We have this original bug report which contains the overall bug that was trying to be fixed:
<bug_report>
{original_bug_report}
</bug_report>

When we encountered the bug, we made a session recording that took screenshots at certain points. We also replayed the actions from the recording on the version of the application after the fix was made.

We validate whether the bug is fixed by looking at every single paired screenshot from the before and after recordings. You'll be looking at a single snapshot (before and after image) of this recording with respect to the bug report we made.

The user has this annotation made to help you with this evaluation.
{test_case}

If you think this snapshot is not relevant, put that it was succesful so that it is not counted as a failure. Think critically about the images
"""
    )
