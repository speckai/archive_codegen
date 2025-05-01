from pathlib import Path

from src.agents.implementer.utils.fs import write_file
from src.agents.implementer.utils.persistent_shell import (
    _PersistentShell,
    get_persistent_shell,
)


def is_in_directory(target_path: str, base_path: str) -> bool:
    """Check if target_path is within base_path directory."""
    try:
        target: Path = Path(target_path).resolve()
        base: Path = Path(base_path).resolve()

        return target == base or base in target.parents
    except Exception:
        return False


async def get_file_mtime(filepath: str) -> float | None:
    """
    Get file modification time from the sandbox environment.

    Args:
        filepath: Path to the file in the sandbox

    Returns:
        float: Unix timestamp of file modification time, or None if failed
    """
    try:
        full_path: str = str(Path(filepath).resolve())
        shell: _PersistentShell = get_persistent_shell()
        stat_result = await shell.exec(f"stat -c %Y '{full_path}'")
        if stat_result["code"] == 0 and stat_result["stdout"].strip():
            return float(stat_result["stdout"].strip())
        return None
    except Exception as e:
        print(f"Error getting modification time for {filepath}: {e}")
        return None


async def write_text_content(
    file_path: str, content: str, enc: str, endings: str
) -> None:
    to_write = "\r\n".join(content.split("\n")) if endings == "CRLF" else content
    await write_file(file_path, to_write, enc, endings)
