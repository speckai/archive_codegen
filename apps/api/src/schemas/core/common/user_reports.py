from typing import Any

from pydantic import BaseModel


class ReportAssetModel(BaseModel):
    """Base model for bug report assets that will be sent to the frontend directly."""

    artifact_id: str
    content_type: str
    markdown_format: str
    data: dict[str, Any] = {}


class BugReport(BaseModel):
    """
    Result of bug report generation including the report, asset URLs, and text models.

    Contains validation flags for implementation systems to use when processing.
    """

    report: str
    asset_urls: dict[str, str]
    text_models: dict[str, ReportAssetModel] = {}
    is_implementation_ready: bool = (
        True  # TODO: remove these three attrs? idk what they do
    )
    implementation_flags: dict[str, bool] = {
        "has_file_references": False,
        "has_valid_assets": False,
        "has_detailed_steps": False,
    }
    implementation_notes: str = ""


class IssueContents(BaseModel):
    content: str
    asset_urls: dict[str, str]
    text_models: dict[str, ReportAssetModel]
