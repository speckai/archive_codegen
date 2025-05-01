import os

from src.agents.implementer.models import FullToolUseResult
from src.agents.implementer.tools.ls.tool import LSInput, LSTool
from src.agents.implementer.utils.fs import exists, read_file
from src.agents.implementer.utils.persistent_shell import get_cwd
from src.agents.implementer.utils.ripgrep import rip_grep
from src.utils.logging import logger


async def get_directory_structure():
    results: FullToolUseResult = await LSTool().call(LSInput(path=get_cwd()), None)
    return f"""Below is a snapshot of this project's file structure at the start of the conversation. This snapshot will NOT update during the conversation.
    {results.data}
    """


async def get_readme():
    readme_path: str = os.path.join(get_cwd(), "README.md")
    logger.debug(f"readme_path: {readme_path}")
    if not await exists(readme_path):
        logger.debug(f"README.md not found at {readme_path}")
        return None
    return await read_file(readme_path, "utf-8")


async def get_claude_files():
    files: list[str] = await rip_grep(
        ["--files", "--glob", "**/*/CLAUDE.md"], get_cwd()
    )
    if not files:
        return None
    return f"""
    NOTE: Additional CLAUDE.md files were found. When working in these directories, make sure to read and follow the instructions in the corresponding CLAUDE.md file:
    {"\n".join(files)}
    """


async def get_context():
    return {
        "directory_structure": await get_directory_structure(),
        "claude_files": await get_claude_files(),
        "readme": await get_readme(),
    }
