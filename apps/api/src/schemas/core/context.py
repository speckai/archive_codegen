from pydantic import BaseModel, Field


class Questions(BaseModel):
    change_request_thinking: str = Field(
        ...,
        description="Place for you to think before asking questions.",
    )
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
    response_message: str = Field(
        ...,
        description="First person acknowledgement of the request and say you will make the changes. Start with saying 'thank you for answering the questions', say the changes you will make in no longer than 10 words, then say you'll let the user know when you're done.",
    )


class RequestChangeResponse(BaseModel):
    response_message: str = Field(
        ...,
        description="First person acknowledgement of the request and say you will make the changes. Start with saying 'I'll start working on the changes now', say the changes you will make in no longer than 10 words, then say you'll let the user know when you're done.",
    )
