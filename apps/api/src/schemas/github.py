from datetime import datetime

from pydantic import BaseModel


class GitHubUser(BaseModel):
    id: int
    login: str
    avatar_url: str
    html_url: str


class GitHubComment(BaseModel):
    id: int
    user: GitHubUser
    body: str
    created_at: datetime
    updated_at: datetime | None = None
    html_url: str


class GitHubLabel(BaseModel):
    id: int
    name: str
    color: str
    description: str | None = None


class GitHubIssue(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = None
    state: str
    html_url: str
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    user: GitHubUser
    assignees: list[GitHubUser] = []
    labels: list[GitHubLabel] = []
    comments: list[GitHubComment] = []
    repository_id: int
    repository_name: str
    repository_owner: str


class GitHubRepository(BaseModel):
    id: int
    name: str
    owner: str


class IssueResponse(BaseModel):
    title: str
    description: str | None = None
    number: int
    state: str
    url: str
    repository: GitHubRepository


class IssueDetailsResponse(BaseModel):
    success: bool
    issue: IssueResponse | None = None
