from pydantic import BaseModel


class ContainerInfo(BaseModel):
    user_id: str
    session_id: str
    task_id: str  # AWS ECS task ID or local task ID
    container_ip: str | None = None
    container_port: int = 8000
    preview_port: int | None = None
    status: str
    created_at: float
    is_warm: bool


class ContainerRequest(BaseModel):
    user_id: str
    session_id: str
