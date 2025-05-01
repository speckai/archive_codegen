from src.utils.prompt_utils import format_prompt


def URL_GENERATION_SYSTEM() -> str:
    return format_prompt(
        """
    You are an expert at analyzing code changes to determine affected URL routes.
    Analyze git diffs to identify which URL paths in the application might be affected.
    """
    )


def URL_GENERATION_PROMPT(
    issue_description: str,
    diffs: str,
    file_tree: str,
    test_cases: str,
    all_valid_urls: str,
) -> str:
    return format_prompt(
        f"""
    <issue_description>
    {issue_description}
    </issue_description>

    <git_diffs>
    {diffs}
    </git_diffs>
    
    <file_tree>
    {file_tree}
    </file_tree>

    <test_cases>
    {test_cases}
    </test_cases>

    <all_valid_urls>
    {all_valid_urls}
    </all_valid_urls>
    
    Based on these changes, determine which URL paths in the application might be affected.
    Consider:
    1. Changes to route files (/, /about, /contact, etc.)
    2. Changes to components used on specific pages
    3. Changes to shared layouts that affect multiple pages
    
    Return a list of URL paths (starting with /) that should be tested for runtime errors.
    """
    )
