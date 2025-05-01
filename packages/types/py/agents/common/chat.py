from enum import StrEnum

from pydantic import BaseModel

from .files import ApiRequest, SelectedComponent


class ChatMessageRole(StrEnum):
    PAIGE = "paige"
    USER = "user"


class ChatMessageType(StrEnum):
    INITIAL_USER_MESSAGE = "initial_user_message"
    SIMPLE_MESSAGE = "simple_message"
    QUESTIONS = "questions"


class UserInitialMessage(BaseModel):
    message: str
    api_requests: list[ApiRequest]
    selected_components: list[SelectedComponent]


class UnansweredQuestions(BaseModel):
    questions: list[str]


class AnsweredQuestions(BaseModel):
    questions: list[dict[str, str]]


class SimpleMessage(BaseModel):
    message: str


class ChatMessage(BaseModel):
    role: ChatMessageRole
    message_type: ChatMessageType
    message: UnansweredQuestions | AnsweredQuestions | SimpleMessage
