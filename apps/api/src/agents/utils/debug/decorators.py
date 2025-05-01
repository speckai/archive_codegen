import functools
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel
from src.agents.utils.base_agent import BaseAgent
from src.utils.logging import logger

T = TypeVar("T")
AgentType = TypeVar("AgentType", bound=BaseAgent)


def debug_agent_function(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for agent functions that records debug information when in debug mode.
    Records:
    - Function input args
    - Agent name
    - Debug actions up to this point
    - Timestamp
    """

    @functools.wraps(func)
    async def wrapper(self: AgentType, *args, **kwargs):
        if not self.task.debug or self.task.debug.debug_agent:
            return await func(self, *args, **kwargs)

        # Get agent name from class
        agent_name = self.__class__.__name__

        # Create debug directory structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = Path.cwd() / ".debug" / agent_name / func.__name__ / timestamp
        debug_dir.mkdir(parents=True, exist_ok=True)

        # Convert args and kwargs to JSON-serializable format
        converted_args = [
            arg.model_dump() if isinstance(arg, BaseModel) else arg for arg in args
        ]
        converted_kwargs = {
            k: v.model_dump() if isinstance(v, BaseModel) else v
            for k, v in kwargs.items()
        }

        # Prepare debug data
        debug_data = {
            "agent": agent_name,
            "function": func.__name__,
            "timestamp": timestamp,
            "args": converted_args,
            "kwargs": converted_kwargs,
            "debug_actions": self.task.debug_actions.copy(),
            "debug_settings": {
                "user": self.task.user.model_dump_json(),
                "repo_dir": str(self.task.debug.repo_dir),
                "original_repo_dir": str(self.task.debug.original_repo_dir),
                "env_file": (
                    str(self.task.debug.env_file) if self.task.debug.env_file else None
                ),
            },
            "initial_commit": self.task.debug.initial_commit,
            "target_commit": self.task.debug.target_commit,
            "current_workflow.context": (
                self.task.current_workflow.context.model_dump_json()
                if self.task.current_workflow and self.task.current_workflow.context
                else None
            ),
            "chat.history": [
                message.model_dump_json() for message in self.task.chat.history
            ],
        }

        # Save debug data as JSON
        debug_file = debug_dir / "debug_data.json"
        with open(debug_file, "w") as f:
            json.dump(debug_data, f, indent=2)

        logger.info(f"Debug data saved to {debug_file}")

        # Execute function
        result = await func(self, *args, **kwargs)
        return result

    return wrapper
