from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.agents.implementer.models import FullToolUseResult, ToolUseContext


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the tool"""
        pass

    @property
    @abstractmethod
    def prompt(self) -> str:
        """Return the prompt for the tool"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> BaseModel:
        """Return the input schema for the tool"""
        pass

    @property
    @abstractmethod
    def is_read_only(self) -> bool:
        """Return whether the tool is read-only"""
        pass

    @abstractmethod
    async def validate_input(
        self, input: dict[str, Any], context: Any = None
    ) -> dict[str, Any]:
        """Validate the input for the tool"""
        pass

    @abstractmethod
    async def call(
        self, input: BaseModel, context: "ToolUseContext"
    ) -> "FullToolUseResult":
        """Call the tool with the given input"""
        pass

    def to_dict(self) -> dict:
        """Convert tool to a JSON-serializable dictionary for the Anthropic API"""
        schema_model: BaseModel = self.input_schema
        schema_dict: dict = schema_model.model_json_schema()

        return {
            "name": self.name,
            "description": self.prompt,
            "input_schema": {
                "type": "object",
                "properties": schema_dict.get("properties", {}),
                "required": schema_dict.get("required", []),
            },
        }
