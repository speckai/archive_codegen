import shlex

SINGLE_QUOTE = "__SINGLE_QUOTE__"
DOUBLE_QUOTE = "__DOUBLE_QUOTE__"
COMMAND_LIST_SEPARATORS = {"&&", "||", ";", ";;"}


def split_command(command: str) -> list[str]:
    modified_command: str = command.replace('"', f'"{DOUBLE_QUOTE}').replace(
        "'", f"'{SINGLE_QUOTE}"
    )

    parts: list[str | dict] = []
    try:
        lexer: shlex.shlex = shlex.shlex(modified_command)
        lexer.whitespace_split = True
        tokens: list[str | dict] = list(lexer)

        for token in tokens:
            if parts and isinstance(parts[-1], str) and isinstance(token, str):
                parts[-1] += " " + token
            else:
                parts.append(token)
    except ValueError:
        return [command]

    string_parts: list[str] = []
    for part in parts:
        if isinstance(part, str):
            string_parts.append(part)

    quoted_parts: list[str] = [
        part.replace(SINGLE_QUOTE, "'").replace(DOUBLE_QUOTE, '"')
        for part in string_parts
        if part
    ]

    return [part for part in quoted_parts if part not in COMMAND_LIST_SEPARATORS]
