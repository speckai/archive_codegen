from typing import Optional

from pydantic import BaseModel
from src.schemas.account import User


class TestConfig(BaseModel):
    # Required fields
    repo_dir: str
    initial_commit: str
    target_commit: str
    evaluator_text: str
    user_input: str
    user: User

    # Optional fields with defaults
    url_paths: Optional[list[str]] = None
    node_modules_cache_dir: str = "node_modules_cache"
    skip_install: bool = False
    cached_node_modules_path: Optional[str] = None
    env_file: Optional[str] = None
