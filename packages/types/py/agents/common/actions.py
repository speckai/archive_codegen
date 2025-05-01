from enum import StrEnum
from typing import Union

from pydantic import BaseModel

from .modifications import ModificationsPlan


class ActionToPerform(StrEnum):
    IMPLEMENT = "implement"
    SEARCH = "search"


class ShortCircuitAction(BaseModel):
    action: ActionToPerform
    ask_clarifying_questions: bool
    modifications_plan: Union[
        ModificationsPlan, None
    ]  # Not None if action is IMPLEMENT
