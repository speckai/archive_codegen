from typing import TYPE_CHECKING

from src.utils.prompt_utils import format_prompt

if TYPE_CHECKING:
    from src.schemas.core.implementer import AttemptedCommandResponse


def RUN_COMMAND_USER_PROMPT(
    purpose: str,
    thinking: str,
    command: str,
    task_context: str,
    dependencies_xml: str,
    special_instructions_to_follow: str,
) -> str:
    return format_prompt(
        f"""
The assistant is about to execute a command on the system. The following information is provided:

1. The purpose of this command:
<purpose>
{purpose}
</purpose>

2. The thought process of the developer who wrote this step:
<thinking>
{thinking}
</thinking>

3. The suggested command that the developer said the assistant should run:
<command>
{command}
</command>

4. The context of the task the user is trying to complete:
<task_context>
{task_context}
</task_context>

5. The dependencies and devDependencies from package.json:
{dependencies_xml}

6. Special instructions to follow:
{special_instructions_to_follow}

The assistant should:
1. Analyze the provided thought process and the suggested command.
2. Verify if the command will work as intended. Think specifically about if the command exists, if it's compatible with the current dependencies, when your information was last updated and other context.
3. If necessary, modify the command to ensure it functions correctly.

If we're installing dependencies, make sure we consider what dependencies we need, and add more if necessary to accomplish the overall goal.

If using Chakra UI, make sure to install Chakra UI V2 with the SPECIFIC version in the command.

If we're using a CLI like shadcn, make sure to use a package executer.
    - Example: not "bun shadcn@latest add ...", but "bunx shadcn@latest add ..."

Shadcn commands use "shadcn" not "shadcn-ui".
    - Example: not "bunx shadcn-ui@latest add ...", but "bunx shadcn@latest add ..."

If we're using `tsc`, make sure to use `tsc --noEmit ----noEmit --allowJs --checkJs`. \
Also make sure we use the package executer, like `npx` or `bunx`.
    - Example: `npx tsc --noEmit --allowJs --checkJs`, not `pnpm exec tsc --noEmit --allowJs --checkJs`

<example_1>
<suggested_command>bunx shadcn-ui@latest add alert-dialog</suggested_command>
<modified_command>bunx shadcn@latest add alert-dialog</modified_command>
<explanation>The command was to add an alert dialog component to the project, but shadcn-ui got renamed to shadcn. \
    This means the command should be bunx shadcn@latest add alert-dialog, not bunx shadcn-ui@latest add alert-dialog.</explanation>
</example_1>

<example_2>
<suggested_command>npm i @chakra-ui/react</suggested_command>
<modified_command>npm i @chakra-ui/react@2.0.0</modified_command>
<explanation>The command was to install Chakra UI, but for Chakra UI we need to install the V2 version. \
    This means the command should be npm i @chakra-ui/react@2.0.0, not npm i @chakra-ui/react.</explanation>
</example_2>

Respond with:
1. The assistant's analysis and reasoning wrapped in <thinking></thinking> tags.
2. The final command wrapped in <command></command> tags.
"""
    )


def RUN_COMMAND_WITH_ERRORS_USER_PROMPT(
    purpose: str,
    thinking: str,
    initial_command: str,
    last_attempted_command: "AttemptedCommandResponse",
    previous_attempts: list["AttemptedCommandResponse"],
    dependencies_xml: str,
    special_instructions_to_follow: str,
) -> str:
    return format_prompt(
        f"""
The assistant has tried to run a command, but it failed. We need to fix the command and try again.

The purpose of this command:
<purpose>
{purpose}
</purpose>

The thought process of the developer who wrote this step:
<thinking>
{thinking}
</thinking>

The original suggested command that the developer said the assistant should run:
<command>
{initial_command}
</command>

The last command we tried to run:
<last_attempted_command>
{last_attempted_command.xml}
</last_attempted_command>

Previous attempts we've tried to run this command:
<previous_attempts>
{"\n".join(attempt.xml_with_index(index) for index, attempt in enumerate(previous_attempts))}
</previous_attempts>

The dependencies and devDependencies from package.json:
{dependencies_xml}

Special instructions to follow:
{special_instructions_to_follow}

The assistant should:
1. Analyze all the context provided carefully.
2. Draft a new command that will accomplish the purpose without erroring. \
Think specifically about if the command exists, if it's compatible with the current dependencies, when your information was last updated and other context.

If we're installing dependencies, make sure we consider what dependencies we need, and add more if necessary to accomplish the overall goal.

If using Chakra UI, make sure to install Chakra UI V2 with the SPECIFIC version in the command.

If we're using a CLI like shadcn, make sure to use a package executer.
    - Example: not "bun shadcn@latest add ...", but "bunx shadcn@latest add ..."

Shadcn commands use "shadcn" not "shadcn-ui".
    - Example: not "bunx shadcn-ui@latest add ...", but "bunx shadcn@latest add ..."
"""
    )


def CLASSIFY_ERRORS_SYSTEM_PROMPT() -> str:
    return format_prompt(
        """
You are a senior React developer that looks at a command output and determines if the command succeeded or not. \
You will be given a command, the output of the command, and the errors from the command. You will need to determine if the command worked as the developer intended. \
If they are critical, we will then send that to the developer to think and try a different command.
        """
    )


def CLASSIFY_ERRORS_USER_PROMPT(
    purpose: str,
    thinking: str,
    attempted_command: str,
    output: str,
    errors: str,
) -> str:
    return format_prompt(
        f"""
The purpose of the command:
<purpose>
{purpose}
</purpose>

The thought process of the developer who wrote this step:
<thinking>
{thinking}
</thinking>

The command we tried to run:
<command>
{attempted_command}
</command>

The output of the command:
<output>
{output}
</output>

The errors from the command:
<errors>
{errors}
</errors>

You are to think deeply about the output and errors and determine if the command worked as the developer intended.

The command worked as intended if the output is what the developer intended. Even if there were errors, if the output is what the developer intended, the command worked as intended.
For example if we're compiling the code and the command output has errors, the command worked as intended because the developer intended to find errors.

<example_1>
<command>bunx tsc --noEmit --allowJs --checkJs</command>
<output>app/components/Header.tsx(2,1): error TS2349: This expression is not callable.</output>
<errors>Type 'String' has no call signatures.
app/page.tsx(1,20): error TS2306: File '/app/repo--1/app/components/Header.tsx' is not a module.</errors>
<classification>Since the purpose of the command is to find errors, the command worked as intended. Even though there were errors, we expected them and the purpose of the command\
was to compile the code to check for errors. This means the command resulted in the result the developer intended.</classification>
</example_1>

<example_2>
<command>npm install @nonexistent/ui-library</command>
<output>npm ERR! code E404
npm ERR! 404 Not Found - GET https://registry.npmjs.org/@nonexistent%2Fui-library - Not found
npm ERR! 404 
npm ERR! 404  '@nonexistent/ui-library@latest' is not in this registry.</output>
<errors>npm ERR! A complete log of this run can be found in: /root/.npm/_logs/2024-03-14T12_34_56_789Z-debug.log</errors>
<classification>The command did not work as intended.\
The developer wanted to install a UI library but the package does not exist in the npm registry.\
This means the command failed to achieve its purpose of installing the required dependency.</classification>
</example_2>
"""
    )
