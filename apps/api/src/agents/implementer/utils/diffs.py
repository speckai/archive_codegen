import difflib

CONTEXT_LINES = 3

AMPERSAND_TOKEN = "<<:AMPERSAND_TOKEN:>>"
DOLLAR_TOKEN = "<<:DOLLAR_TOKEN:>>"


def get_patch(
    file_path: str, file_contents: str, old_str: str, new_str: str
) -> list[dict]:
    safe_contents: str = file_contents.replace("&", AMPERSAND_TOKEN).replace(
        "$", DOLLAR_TOKEN
    )
    safe_old: str = old_str.replace("&", AMPERSAND_TOKEN).replace("$", DOLLAR_TOKEN)
    safe_new: str = new_str.replace("&", AMPERSAND_TOKEN).replace("$", DOLLAR_TOKEN)

    edited_contents: str = safe_contents.replace(safe_old, safe_new)

    original_lines: list[str] = safe_contents.splitlines()
    edited_lines: list[str] = edited_contents.splitlines()

    diff: list[str] = difflib.unified_diff(
        original_lines,
        edited_lines,
        fromfile=file_path,
        tofile=file_path,
        n=CONTEXT_LINES,
        lineterm="",
    )

    hunks: list[dict] = []
    current_hunk: dict | None = None

    for line in diff:
        # Skip the first two lines (file headers)
        if line.startswith("---") or line.startswith("+++"):
            continue

        # Start of a new hunk
        if line.startswith("@@"):
            # Parse the hunk header
            parts: list[str] = line.split(" ")
            # Format: @@ -start,length +start,length @@
            from_info: list[str] = parts[1][1:].split(",")  # Remove the '-' prefix
            to_info: list[str] = parts[2][1:].split(",")  # Remove the '+' prefix

            from_start: int = int(from_info[0])
            from_length: int = int(from_info[1]) if len(from_info) > 1 else 1
            to_start: int = int(to_info[0])
            to_length: int = int(to_info[1]) if len(to_info) > 1 else 1

            current_hunk: dict = {
                "oldStart": from_start,
                "oldLines": from_length,
                "newStart": to_start,
                "newLines": to_length,
                "lines": [],
            }
            hunks.append(current_hunk)
        elif current_hunk is not None:
            # Replace tokens with original characters
            line: str = line.replace(AMPERSAND_TOKEN, "&").replace(DOLLAR_TOKEN, "$")
            current_hunk["lines"].append(line)

    return hunks
