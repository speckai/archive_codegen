from enum import StrEnum

from pydantic import BaseModel, Field

from .modifications import ModificationsPlan


class ActionToPerform(StrEnum):
    IMPLEMENT = "implement"
    SEARCH = "search"


class ShortCircuitAction(BaseModel):
    action: ActionToPerform
    ask_clarifying_questions: bool
    modifications_plan: ModificationsPlan | None  # Not None if action is IMPLEMENT


class GitAction(StrEnum):
    COMMIT_AND_PUSH = "commit_and_push"
    COMMIT = "commit"
    COLLECT_CONTEXT = "collect_context"


class GitActions(BaseModel):
    thinking: str = Field(
        ..., description="A message to the user about what Speck is thinking."
    )
    git_action: GitAction = Field(..., description="The action to take.")
    context: str = Field(
        ...,
        description="ONLY if the git_action is COLLECT_CONTEXT. This should ask the user a question to guide them to either push or ",
    )


class MessageAction(StrEnum):
    TASK = "task"
    QUESTION = "question"
    GIT = "git"
    VALIDATE_BUILD = "validate_build"
    UNDEFINED = "undefined"


class MessageIntent(BaseModel):
    thinking: str = Field(..., description="The user is thinking about the task")
    action: MessageAction = Field(..., description="The action the user wants to take")
    relevant_chats: list[int] = Field(
        ...,
        description="Indices of messages that will be given to the routed agent. These should be ONLY messages that will be used for the task.",
    )
