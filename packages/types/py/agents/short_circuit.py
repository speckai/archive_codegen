from pydantic import BaseModel, Field

from .common.actions import ActionToPerform


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
    modified_urls: list[str] = Field(
        ...,
        description="List of specific relative URLs that will be affected by the changes. Use concrete, browser-accessible paths (e.g., '/blog/example-post' instead of '/blog/[slug]').",
    )
    summary: str = Field(
        ...,
        description="ONLY add this if performing an IMPLEMENT. This will be displayed to the user AFTER the plan has been implemented.",
    )
