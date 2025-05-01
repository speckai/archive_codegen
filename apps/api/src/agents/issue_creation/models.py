"""
Models for the issue creation agent.
"""

from pydantic import BaseModel, Field


class IssueValidationResult(BaseModel):
    """Result of validating an issue description"""

    reason: str = Field(
        ..., description="Explanation of why the issue description is valid or invalid"
    )
    is_valid: bool = Field(
        ..., description="Whether the issue description meets the quality criteria"
    )
    improvement_suggestions: list[str] = Field(
        ...,
        description="Suggestions for improving the issue description if it's invalid",
    )
    do_deep_research: bool = Field(
        ...,
        description="Whether to perform deep research on the issue description. If there are files missing from the issue description, we will perform deep research to find them. Expensive operation so only do it if there are files missing that you are sure are needed.",
    )
