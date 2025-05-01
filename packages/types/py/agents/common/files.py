from pydantic import BaseModel


class SelectedComponent(BaseModel):
    name: str
    file_path: str
    line_number: int
    change_message: str


class SelectedComponents(BaseModel):
    selected_components: list[SelectedComponent]


class FileSearchResult(BaseModel):
    file_path: str
    content: str
    total_score: float


class ApiRequest(BaseModel):
    curl: str
    description: str
    response: str
