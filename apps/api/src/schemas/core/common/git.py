from pydantic import BaseModel, Field


class CommitMessage(BaseModel):
    thinking: str = Field(
        ...,
        description="A message to the user about what Speck is thinking.",
    )
    commit_description: str = Field(
        ...,
        description="Hyphenated bullet point list of changes. This should highlight every change done.",
    )
    commit_message: str = Field(
        ..., description="Brief descriptive commit message in no longer than 10 words"
    )


class GitBranch(BaseModel):
    thinking: str = Field(
        ...,
        description="A message to the user about what Speck is thinking.",
    )
    branch_name: str = Field(
        ...,
        description="The name of the branch to create.",
    )
