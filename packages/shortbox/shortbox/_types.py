from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class SandboxException(BaseException):
    pass


class ContainerInfo(BaseModel):
    user_id: str
    session_id: str
    task_id: str  # AWS ECS task ID or local task ID
    container_ip: str | None = None
    container_port: int = 8000
    preview_port: int | None = None
    status: str
    created_at: float


class CommandMode(StrEnum):
    STREAM = "stream"
    WAIT = "wait"
    BACKGROUND = "background"


class CommandOutput(BaseModel):
    output: str
    type: Literal["stdout", "stderr"]
    process_id: str | int


class CommandExit(BaseModel):
    exit_code: int
    process_id: str | int


class CommandResult(BaseModel):
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None


class Status(BaseModel):
    running: bool | None


class CommandKilled(BaseModel):
    status: str
    exit_code: int | None = None


class CommandError(BaseModel):
    error: str
