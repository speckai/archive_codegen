from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ResolutionPreset(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @property
    def dimensions(self) -> tuple[int, int]:
        return {
            ResolutionPreset.SMALL: (640, 360),
            ResolutionPreset.MEDIUM: (1280, 720),
            ResolutionPreset.LARGE: (1920, 1080),
        }[self]


class TestCase(BaseModel):
    test_instructions: str = Field(
        ..., description="The description and instructions for the test"
    )
    resolution: ResolutionPreset
    url: str = Field(..., description="URL path starting with / (e.g. '/about')")
    validation_criteria: str = Field(
        ..., description="The criteria that define success"
    )


class ValidationResult(BaseModel):
    success: bool
    message: str
    screenshots: list[str]


class ValidationBoundingBox(BaseModel):
    """Structured validation response from Gemini model"""

    success: bool = Field(description="Whether the validation criteria were met")
    message: str = Field(description="Detailed validation feedback")
    relevant_bounding_boxes: list[list[int]] = Field(
        description="List of bounding boxes in [x1,y1,x2,y2] format for relevant UI elements"
    )


class ValidationAction(BaseModel):
    type: Literal["validation"]
    expected_result: str
    is_final_step: bool


class TestPlan(BaseModel):
    thinking: str = Field(..., description="The agent's thinking")
    urls_to_test: list[str] = Field(..., description="The URL paths to test")
    test_cases: list[TestCase] = Field(
        ..., description="List of test cases with their own resolutions"
    )


class TestResult(BaseModel):
    validation_results: list[ValidationResult]
