from typing import TYPE_CHECKING, Any, Type

import socketio
from pydantic import BaseModel
from src.schemas.core.common import AgentStatus, MessageType, WorkflowState
from src.schemas.llm import Model
from src.socket_manager import get_socket
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class BaseAgent:
    def __init__(self, task: "Task"):
        calling_agent_name: str = self.__class__.__name__
        self._status: dict[str, any] = {"status": AgentStatus.IDLE, "actions": []}
        self.agent_name = calling_agent_name.lower().replace("agent", "_agent")
        self.task: Task = task
        self.cumulative_tokens: int = 0

    def __del__(self):
        self.set_agent_status(AgentStatus.IDLE)

    def set_agent_status(self, status: AgentStatus) -> None:
        self._status["status"] = status

    def get_status_dict(self) -> dict[str, any]:
        return self._status.copy()

    async def llm_response(
        self,
        model_type: Model,
        system: str,
        message: str | list[dict[str, str]],
        response_model: BaseModel | Type[str] = str,
        stream: bool = False,
        log_tokens: bool = False,
        **kwargs,
    ) -> Any:
        import json
        import pathlib
        from datetime import datetime

        base_dir = pathlib.Path("temp_llm_output")
        task_dir = base_dir / str(self.task.task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        dump_data = {
            "timestamp": datetime.now().isoformat(),
            "model_type": str(model_type),
            "system": system,
            "message": message,
            "response_model": str(response_model),
            "stream": stream,
            "log_tokens": log_tokens,
            "agent_name": self.agent_name,
            "additional_args": kwargs,
        }

        filename = f"llm_request_{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = task_dir / filename

        with open(filepath, "w") as f:
            json.dump(dump_data, f, indent=2)

        if log_tokens:
            tokens: int = 0
            if isinstance(message, list):
                for msg in message:
                    # assume its like [{'role': 'user', 'content': 'hello'}]
                    tokens += len(msg.values()[1])
            else:
                tokens = len(message)
            tokens = tokens // 4
            logger.debug(f"log_tokens: {log_tokens}")
            self.cumulative_tokens += tokens
            logger.debug(f"cumulative_tokens: {self.cumulative_tokens}")

        response = await self.task.llm_chat(
            model_type=model_type,
            system=system,
            message=message,
            caller=self.agent_name,
            response_model=response_model,
            stream=stream,
            **kwargs,
        )

        dump_data["response"] = str(response)
        with open(filepath, "w") as f:
            json.dump(dump_data, f, indent=2)

        return response

    async def send_update_data(self, type: MessageType, data: dict) -> None:
        if self.task.debug:
            return
        await self.task.send_update_data(type, data)

    async def send_state_update(self, state: WorkflowState):  # TODO: Fix this
        if self.task.debug:
            return
        await self.task.task_state_manager.send_state_update(state)

    def on(self, event: str, handler: callable) -> None:
        if self.task.debug:
            logger.debug(f"Ignoring creating event '{event}'")
            return
        sio: socketio.AsyncServer = get_socket()

        @sio.on(event)
        async def wrapper(socket_id, *args, **kwargs):
            rooms: list[str] = sio.rooms(socket_id)
            if self.task.user.id in rooms:
                await handler(socket_id, *args, **kwargs)
