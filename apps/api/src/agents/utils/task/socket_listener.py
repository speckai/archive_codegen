import asyncio
import time
from typing import TYPE_CHECKING

import socketio
from src.schemas.core.common import MessageType
from src.socket_manager import get_socket
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class SocketListener:
    def __init__(self, task: "Task", event_name: str, message_type: MessageType):
        self.task: Task = task
        self.event_name: str = event_name
        self.message_type: MessageType = message_type

        self.received_data: dict = None
        self.event: asyncio.Event = asyncio.Event()
        self._on(event_name, self._on_data_received)

    async def _on_data_received(self, socket_id: str, data: dict):
        self.received_data = data
        self.event.set()

    def _on(self, event: str, handler: callable) -> None:
        sio: socketio.AsyncServer = get_socket()

        @sio.on(event)
        async def wrapper(socket_id: str, *args, **kwargs):
            rooms: list[str] = sio.rooms(socket_id)
            if self.task.task_id in rooms:
                await handler(socket_id, *args, **kwargs)

    async def request_data(self, data: dict) -> dict:
        start_time: float = time.time()
        logger.trace(f"Requesting data for {self.message_type}")
        await self.task.send_update_data(self.message_type, data)
        await self.event.wait()
        self.event.clear()
        logger.trace(
            f"Received data for {self.message_type} in {time.time() - start_time} seconds"
        )
        return self.received_data


def listener(event_name: str, message_type: MessageType):
    """
    This decorator is NOT FUNCTIONAL.
    It is used to colocate the listener functions with the methods they are listening for.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
