"""
File formatting utilities for the initial context agent.
"""

from src.agents.recording_bug_report.utils.token_utils import TokenCounter
from src.schemas.core.common.files import FileObject


def format_files_context(
    files: list[FileObject],
    max_tokens: int,
    token_counter: TokenCounter,
) -> str:
    """
    Format files as XML while staying within token limit.

    Args:
        files: List of files to format
        max_tokens: Maximum allowed tokens

    Returns:
        XML formatted string of files within token limit
    """
    xml_parts = ["<files>"]
    current_tokens = token_counter.estimate_tokens("\n".join(xml_parts))

    # Process files in order of importance
    for file_object in files:
        file_xml = f"""
<file>
<path>{file_object.file_path}</path>
<content>\n{file_object.content}\n</content>
</file>"""

        file_tokens = token_counter.estimate_tokens(file_xml)
        if current_tokens + file_tokens > max_tokens:
            xml_parts.append("<!-- Additional files omitted due to token limit -->")
            break

        xml_parts.append(file_xml)
        current_tokens += file_tokens

    xml_parts.append("</files>")
    return "\n".join(xml_parts)
