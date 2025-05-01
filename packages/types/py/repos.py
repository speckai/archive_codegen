from pydantic import BaseModel


class RepoSettings(BaseModel):
    package_manager: str
    port: int
    dev_command: str
    root_directory: str
    branch_name: str
