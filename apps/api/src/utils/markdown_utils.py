import re
from typing import Any

from src.schemas.core.common import ReportAssetModel


def extract_title_and_content(markdown_content: str) -> tuple[str, str]:
    """
    Extract the H1 title from markdown content and return both title and content without the title.

    :param markdown_content: The markdown content to process
    :return: Tuple of (title, content without title)
    """
    title_pattern: str = r"^#\s+(.+?)(?:\n|$)"
    title_match = re.search(title_pattern, markdown_content, re.MULTILINE)
    title: str = title_match[1] if title_match else ""

    if title_match:
        processed_content = re.sub(
            title_pattern, "", markdown_content, count=1, flags=re.MULTILINE
        ).lstrip()
    else:
        processed_content = markdown_content

    return title, processed_content


def enrich_console_logs(markdown_content: str, text_models: dict) -> str:
    """
    Enrich console logs in markdown content by replacing references with details components.

    :param markdown_content: The markdown content containing console log references
    :param text_models: Dictionary containing console log data models
    :return: Enriched markdown content with details components
    """
    pattern: str = r"!?\[([^\]]+)\]\(([^)]+)\)"

    def replace_console_log(match: re.Match) -> str:
        title: str = match[1]
        log_id: str = match[2]

        if log_id not in text_models:
            return match[0]

        asset: ReportAssetModel = text_models[log_id]

        log_data: dict[str, Any] = asset.data
        description: str = log_data.get("description", "")
        context: str = log_data.get("context", "")
        log_info = log_data.get("log", {})

        output: str = log_info.get("output", "")
        traceback: list[str] = log_info.get("traceback", [])

        traceback_formatted: str = "\n".join(f"> > {line}" for line in traceback)

        details_content: str = f"""<details><summary>{title}</summary>
<p>
{description}

**Console Errors**
> {output}
{traceback_formatted}

**Context**
{context}
</p>
</details>"""

        return details_content

    enriched_content: str = re.sub(pattern, replace_console_log, markdown_content)
    return enriched_content


def extract_video_tags(markdown_content: str) -> list[dict[str, str]]:
    """
    Extract video tags from markdown content and return a list of dictionaries containing description and asset URL.

    :param markdown_content: The markdown content to process
    :return: List of dictionaries containing video tag information
    """
    pattern: str = r"!\[([^\]]+)\]\(([^)]+\.webm)\)"
    matches: list[tuple[str, str]] = re.findall(pattern, markdown_content)

    video_tags: list[dict[str, str]] = [
        {"description": desc, "asset": url} for desc, url in matches
    ]

    return video_tags


def replace_video_asset(markdown_content: str, description: str, new_url: str) -> str:
    """
    Replace a video asset URL in markdown content based on its description.

    :param markdown_content: The markdown content containing video tags
    :param description: The description text to match for replacement
    :param new_url: The new URL to replace the existing video asset
    :return: Updated markdown content with replaced video asset
    """
    pattern: str = f"!\\[{re.escape(description)}\\]\\([^)]+\\)"
    replacement: str = f"![{description}]({new_url})"

    updated_content: str = re.sub(pattern, replacement, markdown_content)
    return updated_content
