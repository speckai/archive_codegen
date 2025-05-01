import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.agents.utils.task.debug.settings import DebugSettings
from src.utils.logging import logger


def clean_output(output: str | None) -> str | None:
    # TODO: This should NEVER be none. Figure out why
    if output is None:
        logger.critical("Output is None, check why")
        return None

    ansi_escape = re.compile(r"\x1b\[([0-9]+)(;[0-9]+)*m")
    return ansi_escape.sub("", output)


@dataclass
class Debug:
    """Configuration for headless/debug mode"""

    original_repo_dir: Path
    repo_dir: Path  # Local repository directory
    settings: DebugSettings
    debug_agent: bool = False
    env_file: Optional[Path] = None
    initial_commit: str = ""
    target_commit: str = ""
    user_rules: str | None = None
    repo_rules: str | None = None

    def __post_init__(self):
        self.repo_dir = Path(self.repo_dir).resolve()
        if not self.repo_dir.exists():
            raise ValueError(f"Repository directory does not exist: {self.repo_dir}")
        logger.debug(f"Resolved repo directory: {self.repo_dir}")
