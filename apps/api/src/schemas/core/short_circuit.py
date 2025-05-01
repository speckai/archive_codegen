from pydantic import BaseModel, Field
from src.schemas.core.common import ActionToPerform


class ImplementData(BaseModel):
    description: str = Field(
        ...,
        description="High level description of the change. No longer than 3 sentences.",
    )
    purpose: str = Field(
        ...,
        description="Reword the change into a concise purpose, no longer than 1 sentence.",
    )


class SelectionContextResult(BaseModel):
    reasoning: str = Field(..., description="The reasoning behind the decision")
    action_to_perform: ActionToPerform = Field(
        ...,
        description="The action to perform based on the reasoning. Choose either IMPLEMENT or SEARCH.",
    )
    ask_clarifying_questions: bool = Field(
        ...,
        description="If the user's request is unclear, set this to True to ask clarifying questions in the next step.",
    )
    summary: str = Field(
        ...,
        description="ONLY add this if performing an IMPLEMENT. This will be displayed to the user AFTER the plan has been implemented.",
    )
