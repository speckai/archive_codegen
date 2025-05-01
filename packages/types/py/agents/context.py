from pydantic import BaseModel, Field


class Questions(BaseModel):
    questions: list[str] = Field(
        ...,
        description="List of questions, one per entry.",
    )


class NewPrompt(BaseModel):
    thinking: str = Field(
        ...,
        description="Think step by step about how to format the new prompt",
    )
    prompt: str = Field(
        ...,
        description="Your detailed and improved change request message",
    )
    summary: str = Field(
        ...,
        description="A short overall summary of the requested changes from the new prompt. No more than 5 words",
    )
