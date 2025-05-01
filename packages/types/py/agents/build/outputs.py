from pydantic import BaseModel


class BuildOutput(BaseModel):
    command: str
    output: str
    error_logs: str
    status_code: int
