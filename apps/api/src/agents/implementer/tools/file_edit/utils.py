import difflib
import os
import re
from typing import List, TypedDict

from src.agents.implementer.utils.file_utils import detect_file_encoding
from src.agents.implementer.utils.fs import read_file
from src.agents.implementer.utils.persistent_shell import get_cwd

# For consistency with JS version, define tokens
AMPERSAND_TOKEN = "<<:AMPERSAND_TOKEN:>>"
DOLLAR_TOKEN = "<<:DOLLAR_TOKEN:>>"
CONTEXT_LINES = 3


class Hunk(TypedDict):
    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    lines: List[str]


def get_patch(params: dict[str, str]) -> list[Hunk]:
    """Generate a patch between old and new versions of a file."""

    file_path: str = params["filePath"]
    file_contents: str = params["fileContents"]
    old_str: str = params["oldStr"]
    new_str: str = params["newStr"]

    safe_contents: str = file_contents.replace("&", AMPERSAND_TOKEN).replace(
        "$", DOLLAR_TOKEN
    )
    safe_old: str = old_str.replace("&", AMPERSAND_TOKEN).replace("$", DOLLAR_TOKEN)
    safe_new: str = new_str.replace("&", AMPERSAND_TOKEN).replace("$", DOLLAR_TOKEN)

    edited_contents: str = safe_contents.replace(safe_old, safe_new)

    original_lines: list[str] = safe_contents.splitlines(keepends=True)
    edited_lines: list[str] = edited_contents.splitlines(keepends=True)

    diff: list[str] = difflib.unified_diff(
        original_lines,
        edited_lines,
        fromfile=file_path,
        tofile=file_path,
        n=CONTEXT_LINES,
    )

    hunks: list[Hunk] = []
    current_hunk: Hunk | None = None

    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith("@@"):
            if match := re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line):
                old_start, old_lines, new_start, new_lines = map(int, match.groups())

                current_hunk = {
                    "oldStart": old_start,
                    "oldLines": old_lines,
                    "newStart": new_start,
                    "newLines": new_lines,
                    "lines": [],
                }
                hunks.append(current_hunk)
        elif current_hunk is not None:
            line: str = line.replace(AMPERSAND_TOKEN, "&").replace(DOLLAR_TOKEN, "$")
            current_hunk["lines"].append(line.rstrip("\n"))

    return hunks


async def apply_edit(
    file_path: str, old_string: str, new_string: str
) -> tuple[list[Hunk], str]:
    """Applies an edit to a file and returns the patch and updated file. Does not write the file to disk."""
    original_file: str = ""
    updated_file: str = ""

    if not old_string:
        original_file = ""
        updated_file = new_string
    else:
        full_file_path: str = (
            file_path
            if os.path.isabs(file_path)
            else os.path.join(get_cwd(), file_path)
        )

        enc: str = await detect_file_encoding(full_file_path)
        original_file = await read_file(full_file_path, enc)

        if not new_string:
            if not old_string.endswith("\n") and (old_string + "\n") in original_file:
                updated_file = original_file.replace(old_string + "\n", new_string)
            else:
                updated_file = original_file.replace(old_string, new_string)
        else:
            updated_file = original_file.replace(old_string, new_string)

        if updated_file == original_file:
            raise ValueError(
                "Original and edited file match exactly. Failed to apply edit."
            )

    patch: list[Hunk] = get_patch(
        {
            "filePath": file_path,
            "fileContents": original_file,
            "oldStr": original_file,
            "newStr": updated_file,
        }
    )

    return patch, updated_file


# Number of lines to include before and after the edited section in snippets
N_LINES_SNIPPET = 3


def get_snippet(initial_text: str, old_str: str, new_str: str) -> dict[str, str | int]:
    """Extracts a snippet of text around the replacement location."""
    before: str = initial_text.split(old_str)[0] if old_str in initial_text else ""

    replacement_line: int = len(before.splitlines())

    new_file_lines: list[str] = initial_text.replace(old_str, new_str).splitlines()

    start_line: int = max(0, replacement_line - N_LINES_SNIPPET)
    end_line: int = replacement_line + N_LINES_SNIPPET + len(new_str.splitlines())

    snippet_lines: list[str] = new_file_lines[start_line : end_line + 1]
    snippet: str = "\n".join(snippet_lines)

    return {"snippet": snippet, "startLine": start_line + 1}
