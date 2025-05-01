def PACKAGE_JSON_PROMPT(file_name: str, file_content: str) -> str:
    return f"""
<package_json_file>
<file_name>
{file_name.strip()}
</file_name>
<file_content>
{file_content.strip()}
</file_content>
</package_json_file>
""".strip()


def MONOREPO_DETECTION_PROMPT(
    root_files: str, package_json_files: dict[str, str], readme_files: str = ""
) -> str:
    return f"""
<monorepo_app_instructions>
Detect if a repository is a monorepo, and if so, list all valid React or React-based websites in the monorepo.

Analyze the package.json files to detect valid React or React-based websites. Only consider apps that:
1. Have react and react-dom as dependencies
2. Have a dev/start script that runs a web server (like next dev, react-scripts start, vite, etc.)
3. Are NOT documentation sites (mintlify, docusaurus), Python apps, or other non-React services

Ignore:
- Python apps (usually have scripts like run.sh)
- Documentation sites (mintlify, docusaurus, swagger, storybook, etc.)
- Build packages or libraries
- API and server services (even apps/api)
- Non-web applications
</monorepo_app_instructions>

<root_files>
{root_files}
</root_files>

<readme_files>
{readme_files}
</readme_files>

<package_json_files>
{"\n".join(PACKAGE_JSON_PROMPT(file_name, file_content) for file_name, file_content in package_json_files.items())}
</package_json_files>

<response_format>
You are to return a detection response with the following format:
- Thinking: A chain of thought analysis that goes over all of the context. Determine what is relevant, what is not, then create an argument for why the settings are what they are. If we have multiple package.json files, think about which ones are React apps, and which ones are not.
- is_monorepo: Whether the website is a monorepo or not.
- monorepo_apps: A list of valid React or React-based websites in the monorepo. ONLY if the website is a monorepo.
</response_format>  
""".strip()


def SETTINGS_DETECTION_PROMPT(
    root_files: str,
    package_json_files: dict[str, str],
    readme_files: str,
    previous_attempts: str | None = None,
    current_settings: str | None = None,
    failure_stage: str | None = None,
    output: str | None = None,
    is_error: bool = False,
) -> str:
    return f"""
{
        is_error
        and f"The website has failed during the {failure_stage} stage. Based on the error output, analyze what went wrong and suggest updated settings."
        or ""
    }

{
        previous_attempts
        and f'''
<previous_attempts>
{previous_attempts}
</previous_attempts>
'''.strip()
        or ""
    }

{
        current_settings
        and f'''
<current_settings>
{current_settings}
</current_settings>
'''.strip()
        or ""
    }

{
        output
        and failure_stage
        and f'''
<failure_details>
<stage>{failure_stage}</stage>
<output>
{output}
</output>
</failure_details>
'''.strip()
        or ""
    }

<settings_instructions>
Detect the settings of the React website. When detecting the port, keep in mind the package being used.
For the run command, it should be in terms of the package manager, like `<PACKAGE_MANAGER> run ...` or `<PACKAGE_MANAGER> dev`.

There are 4 package managers: pnpm, npm, yarn, and bun.
- pnpm uses "pnpm-lock.yaml"
- npm uses "package-lock.json"
- yarn uses "yarn.lock"
- bun uses "bun.lockb"

If you find the tsconfig_path, modify the prompt to instruct the LLM to extract the tsconfig_path from the files.
</settings_instructions>

<root_file_paths>
{root_files}
</root_file_paths>

<readme_files>
{readme_files}
</readme_files>

<package_json_files>
{
        "\n".join(
            PACKAGE_JSON_PROMPT(file_name, file_content)
            for file_name, file_content in package_json_files.items()
        )
    }
</package_json_files>

<response_format>
You are to return a detection response with the following format:
- Thinking: A chain of thought analysis that goes over all of the context. Determine what is relevant, what is not, then create an argument for why the settings are what they are. If we have multiple package.json files, think about which ones are React apps, and which ones are not.
- is_monorepo: Whether the website is a monorepo or not.
- settings: Has the following fields:
    - package_manager: The package manager being used.
    - port: The port to run the website on. If no port is found, default to 3000.
    - install_command: The command to install the dependencies. Think hard about this, and try to find supporting evidence in any file given.
    - dev_command: The command to run the website. This MUST be a SINGLE specific command, not multiple commands separated by "||". Choose the BEST command that will most likely work based on the package.json scripts. If there are multiple options, pick the one that is most likely to work, not all of them.
- monorepo_apps: A list of valid React or React-based websites in the monorepo. ONLY if the website is a monorepo.
</response_format>  

{
        is_error
        and "Provide thoughtful analysis of the errors and clear fixes to try in the next attempt."
        or ""
    }
""".strip()
