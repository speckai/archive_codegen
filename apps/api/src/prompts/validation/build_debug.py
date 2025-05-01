from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.schemas.core.validation.debug_actions import (
        DebugPlan,
        FixAction,
        RequestedCommandOutput,
        RequestedFileContents,
    )


def GET_FIX_ACTION_SYSTEM_PROMPT(num_attempts: int) -> str:
    return format_prompt(f"""
You are a senior React engineer working on a project. The project has encountered errors. 

"This is turn #{num_attempts + 1}. You are to think about the errors and provide the next action to take."
""")


def _format_errors(errors: list[str]) -> str:
    return "\n".join([error.strip() for error in errors])


def GET_FIX_ACTION_USER_PROMPT(
    dev_command: str,
    task_context: str,
    extracted_errors: list[str],
    file_paths: str,
    dependencies_xml: str,
    previous_contexts: list["RequestedCommandOutput | RequestedFileContents"],
    performed_actions: list["FixAction"],
) -> str:
    return format_prompt(f"""
The project has failed using `{dev_command}`.

Here is the context of the task the user is trying to complete. Make sure any actions you take are consistent with this context. Do NOT make changes that clash with the user's request:
<task_context>
{task_context}
</task_context>

Here are the errors from the terminal console and browser console:
<errors>
{_format_errors(extracted_errors)}
</errors>

Here are all the file paths in the repository:
<file_paths>
{file_paths}
</file_paths>

Here are the dependencies and dev dependencies in the package.json file:
{dependencies_xml}

Here are the previous contexts you have requested from previous turns:
<previous_contexts>
{"\n".join([context.xml for context in previous_contexts])}
</previous_contexts>

Here are the previous actions you have made:
<previous_actions>
{"\n".join([action.xml_with_index(index) for index, action in enumerate(performed_actions)])}
</previous_actions>

You must pick an action that helps you fix the errors. You can either collect more context, or create a plan to fix the errors. \
Context collectors will add a new turn after this one. Definitive actions will break out of the loop and attempt to fix the errors. \
You must only pick the definitive action when you have found the root cause of the errors. 

If you need to restart the website, do NOT restart it through the terminal. Instead, restart it in the DebugPlan.

Bias towards checking for compiler errors if the errors are unclear. Example for bun:
    - Error: We're in a bun project and getting "Error: Unsupported Server Component type". We don't have any actual file names, so it's unclear where the error is coming from.
    - Solution: Run `bunx tsc --noEmit --allowJs --checkJs` to check for compiler errors.
    - Output: We now see that `Module '"/app/components/navigation"' has no default export.`, which can cause a fatal rendering issue. We can now try to fix that error and see if it fixes the original error.
Make sure to use the right command for the project.

Context collectors actions:
- Run a command: You will receive the output of the command on the next turn. This should not be used to fix the errors, instead this should ONLY be used to collect more context. Example: Do NOT install dependencies, that should only be done by the DebugPlan action.
- Get file contents: You will receive the contents of the file on the next turn.

Definitive actions:
- DebugPlan: You will receive a plan to fix the errors. You will need to perform the steps in the plan.
- DoNothing: You will not take any action. This is only allowed if you are confident that the errors do not matter to actually seeing the contents of the site. This can be errors for telemetry, random errors, etc.
    - This turn will break us out of the loop, so only use it if you are confident that the errors do not matter to actually seeing the contents of the site.
    - You CANNOT use this to skip a turn since you are running linearly. The next turn will be the one that is executed.
    - Example: If we get a posthog configuration error, but the site is still running, we can do nothing. 

Bias towards using less steps rather than more steps so we can be faster, but also make sure the steps are correct.
""")


def IMPLEMENTER_STEP_SYSTEM_PROMPT(
    command: str,
    previous_plan_attempts: list["DebugPlan"],
    previous_contexts: list["RequestedCommandOutput | RequestedFileContents"],
) -> str:
    return format_prompt(f"""
<modifications>
The assistant has access to a React codebase and Linux computer that is the output of the modification.
The assistant is to carefully examine the provided steps, understand the steps, and produce outputs that fulfill the request end to end. 
The assistant is working on a project. The project has encountered errors after running `{command}`. The assistant is to fix the errors.

# Good modifications...
- Fix the root cause of the errors without changing any functionality that is not requested.
- Carefully consider the context of the inputs and use them to inform the best way to implement the changes.

# Don't make modifications that...
- Are not consistent with the existing code or inputs that are given.
- Do not consider the context of the previous and next steps to inform the implementation.

When performing modifications, follow these rules:
1. Break down the task: Use Chain of Thought reasoning. Clearly articulate each logical step in solving the problem, treating each as a distinct part of the overall process.
2. Look at what files in previous epics were modified or created and use that information to inform the best way to implement the changes.
3. Take into consideration the framework that the codebase is built on. Be consistent with the framework's best practices when making changes.
4. Include the complete and updated content of the code snippet if requested, without any truncation or minimization. Don't use "// rest of the code remains the same..." or comments like it.
5. For code that is being written, keep the code style consistent with the rest of the codebase.
6. Fulfill the instructions exactly. The code written should work without errors. Do not assume files exist unless they are found in the file paths provided, the file search results, or the previous/next steps.
</modifications>

<previous_plan_attempts>
{"\n".join([attempt.xml_with_index(index) for index, attempt in enumerate(previous_plan_attempts)])}
</previous_plan_attempts>

<context_requested>
{"\n".join([context.xml for context in previous_contexts])}
</context_requested>

Fix the error in as little steps as possible.
""")
