from src.agents.implementer.models import AssistantMessage
from src.agents.implementer.utils.llm import query_haiku
from src.agents.implementer.utils.messages import extract_tag

MAX_OUTPUT_LENGTH = 30000
BANNED_COMMANDS = [
    "alias",
    "curl",
    "curlie",
    "wget",
    "axel",
    "aria2c",
    "nc",
    "telnet",
    "lynx",
    "w3m",
    "links",
    "httpie",
    "xh",
    "http-prompt",
    "chrome",
    "firefox",
    "safari",
]


def format_output(content: str) -> tuple[int, str]:
    """Format output content by truncating if it exceeds MAX_OUTPUT_LENGTH."""
    if len(content) <= MAX_OUTPUT_LENGTH:
        return {
            "total_lines": len(content.split("\n")),
            "truncated_content": content,
        }

    half_length: int = MAX_OUTPUT_LENGTH // 2
    start: str = content[:half_length]
    end: str = content[-half_length:]
    truncated_lines_count: int = len(content[half_length:-half_length].split("\n"))
    truncated: str = (
        f"{start}\n\n... [{truncated_lines_count} lines truncated] ...\n\n{end}"
    )

    return (
        len(content.split("\n")),
        truncated,
    )


async def get_command_file_paths(command: str, output: str) -> list[str]:
    system_prompt: str = """
Extract any file paths that this command reads or modifies. For commands like "git diff" and "cat", include the paths of files being shown. Use paths verbatim -- don't add any slashes or try to resolve them. Do not try to infer paths that were not explicitly listed in the command output.
Format your response as:
<filepaths>
path/to/file1
path/to/file2
</filepaths>

If no files are read or modified, return empty filepaths tags:
<filepaths>
</filepaths>

Do not include any other text in your response.
    """
    user_prompt: str = f"Command: {command}\nOutput: {output}"
    msg: AssistantMessage = await query_haiku(system_prompt, user_prompt)

    content: str = "".join(
        content.text for content in msg.message.content if content.type == "text"
    )

    filepaths: str | None = extract_tag(content, "filepaths")
    return (
        [fp.strip() for fp in (filepaths or "").split("\n") if fp.strip()]
        if filepaths
        else []
    )
