import textwrap


def format_prompt(prompt: str) -> str:
    """
    Format a prompt string by dedenting and stripping whitespace.
    :param prompt: The input prompt string
    :return: The formatted prompt string
    """
    return textwrap.dedent(prompt).strip()
