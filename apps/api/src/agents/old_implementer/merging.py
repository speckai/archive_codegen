from src.config import session_recorder
from src.schemas.core.implementer import EditFileResponse
from src.utils.logging import logger


async def merge_changes(
    file_contents: str, parsed_response: EditFileResponse
) -> str | None:
    """Merge changes from LLM response into the original file contents."""
    result = file_contents
    for edit in parsed_response.edits:
        if hasattr(edit, "original_code_section") and hasattr(edit, "new_code_section"):
            original_code = edit.original_code_section
            new_code = edit.new_code_section

            # Try direct merge first
            merged = await _algorithm_merge(result, original_code, new_code)
            if merged is not None:
                result = merged
                continue

            merged = await _algorithm_merge(
                result, original_code.strip(), new_code.strip()
            )
            if merged is not None:
                result = merged
                continue

            # If direct merge fails, try splitting into sections
            separator = "// ... (other code)"
            if separator in original_code and separator in new_code:
                logger.warning("Merging multiple sections")
                merged = await _merge_multiple_sections(
                    result, original_code, new_code, separator
                )
                if merged is not None:
                    result = merged
                continue

            # logger.warning("All merge attempts failed for section")

        elif hasattr(edit, "file_contents"):
            if len(parsed_response.edits) > 1:
                logger.warning(
                    "Multiple edits found when full file contents were provided"
                )
            return edit.file_contents

    return result if result != file_contents else None


async def _merge_multiple_sections(
    file_contents: str,
    original_code: str,
    new_code: str,
    separator: str,
) -> str | None:
    """Merge multiple code sections separated by a separator."""
    result: str = file_contents
    original_parts: list[str] = original_code.split(separator)
    new_parts: list[str] = new_code.split(separator)

    for original_part, new_part in zip(original_parts, new_parts):
        merged = await _algorithm_merge(
            result, original_part, new_part
        )  # TODO: Check if this needs a strip()
        if merged is None:
            logger.warning("Algorithm merge failed for section")
            continue
        result = merged

    return result


@session_recorder.async_record()
async def _algorithm_merge(
    content: str,
    original_code: str,
    new_code: str,
) -> str | None:
    """Merge changes using a sophisticated matching algorithm."""
    # Normalize whitespace
    original_code, new_code = _normalize_whitespace(original_code, new_code)

    # Direct replacement if only one instance exists
    if content.count(original_code) == 1:
        return content.replace(original_code, new_code)

    # Use convolution-based matching if exact match not found
    if original_code not in content:
        return await _convolution_merge(content, original_code, new_code)

    return None


def _normalize_whitespace(original_code: str, new_code: str) -> tuple[str, str]:
    """Normalize leading and trailing whitespace in code blocks."""
    while True:
        if not (original_code.startswith("\n") and new_code.startswith("\n")):
            break
        original_code = original_code[1:]
        new_code = new_code[1:]

    while True:
        if not (original_code.endswith("\n") and new_code.endswith("\n")):
            break
        original_code = original_code[:-1]
        new_code = new_code[:-1]

    return original_code, new_code


async def _convolution_merge(
    content: str, original_code: str, new_code: str
) -> str | None:
    """Merge changes using convolution-based matching algorithm."""
    content_lines = content.split("\n")
    original_lines = original_code.split("\n")

    if len(content_lines) < len(original_lines):
        return None

    start_scores = [
        _calculate_match_score(content_lines[i:], original_lines)
        for i in range(len(content_lines) - len(original_lines) + 1)
    ]

    end_scores = [
        _calculate_match_score(content_lines[i:], original_lines, reverse=True)
        for i in range(len(content_lines) - len(original_lines) + 1)
    ]

    if not (start_scores and end_scores):
        logger.warning("Failed to generate convolution scores")
        return None

    max_possible_score = sum(1 / (i + 1) for i in range(len(original_lines)))
    if not _validate_scores(start_scores, end_scores, max_possible_score):
        return None

    start_idx = start_scores.index(max(start_scores))
    end_idx = end_scores.index(max(end_scores)) + len(original_lines)

    if not _validate_section_size(start_idx, end_idx, len(original_lines)):
        return None

    return "\n".join(
        content_lines[:start_idx] + new_code.split("\n") + content_lines[end_idx:]
    )


def _calculate_match_score(
    content_lines: list[str], original_lines: list[str], reverse: bool = False
) -> float:
    """Calculate the match score for a section of content against original lines."""
    line_indices = (
        range(len(original_lines))
        if not reverse
        else range(len(original_lines) - 1, -1, -1)
    )
    return sum(
        (
            1.0 / (i + 1.0)
            if content_lines[line_index].strip() == original_lines[line_index].strip()
            else 0
        )
        for i, line_index in enumerate(line_indices)
    )


def _validate_scores(
    start_scores: list[float], end_scores: list[float], max_possible: float
) -> bool:
    """Validate that the match scores are high enough to be considered valid."""
    threshold = 0.5 * max_possible
    return max(start_scores) >= threshold and max(end_scores) >= threshold


def _validate_section_size(start_idx: int, end_idx: int, original_size: int) -> bool:
    """Validate that the selected section size is close to the original code size."""
    MAX_DIFF = 3
    return abs(original_size - (end_idx - start_idx)) <= MAX_DIFF
