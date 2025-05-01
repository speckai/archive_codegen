from difflib import get_close_matches
from typing import TYPE_CHECKING

from morphcloud.api import InstanceExecResponse
from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.agents.recorder_analyzer.utils.models import FileLocation
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


async def search_codebase_for_keywords(
    task: "Task", keywords: list[str], file_extensions: list[str] | None = None
) -> dict[str, list[str]]:
    """
    Search the codebase for the given keywords, respecting gitignore rules.

    :param task: Task object containing sandbox for command execution
    :param keywords: List of keywords to search for
    :param file_extensions: List of file extensions to search in (e.g. ['ts', 'tsx'])
    :return: Dictionary mapping keywords to lists of matches (file:line:content)
    """
    if file_extensions is None:
        file_extensions = ["ts", "tsx"]

    keyword_results: dict[str, list[str]] = {}

    for keyword in keywords:
        if not keyword.strip():
            continue

        logger.debug(f"Searching for keyword: '{keyword}'")
        try:
            # Build file extension pattern for git ls-files
            extension_patterns: list[str] = [f"'*.{ext}'" for ext in file_extensions]
            extension_pattern_str: str = " ".join(extension_patterns)

            # Use git ls-files to respect gitignore and grep to search for the keyword
            cmd: str = (
                f"""cd /repo && git ls-files -z {extension_pattern_str} | xargs -0 grep -n '{keyword}' || echo 'No results'"""
            )
            result: InstanceExecResponse = await task.sandbox.run_command(cmd)

            if "No results" not in result.stdout:
                matches: list[str] = result.stdout.strip().split("\n")
                keyword_results[keyword] = matches
                logger.debug(f"Found {len(matches)} matches for '{keyword}'")
            else:
                logger.debug(f"No matches found for '{keyword}'")
                keyword_results[keyword] = []
        except Exception as e:
            logger.error(f"Error searching for keyword '{keyword}': {str(e)}")
            keyword_results[keyword] = []

    return keyword_results


async def search_files_by_pattern(
    task: "Task", patterns: list[str], file_extensions: list[str] | None = None
) -> dict[str, list[str]]:
    """
    Search for files matching the given patterns using fuzzy matching.

    :param task: Task object containing sandbox for command execution
    :param patterns: List of file path patterns to search for
    :param file_extensions: List of file extensions to search in
    :return: Dictionary mapping patterns to lists of matching file paths
    """
    if file_extensions is None:
        file_extensions = ["ts", "tsx"]

    # Build file extension pattern for git ls-files
    extension_patterns: list[str] = [f"'*.{ext}'" for ext in file_extensions]
    extension_pattern_str: str = " ".join(extension_patterns)

    try:
        cmd: str = f"cd /repo && git ls-files {extension_pattern_str} | sort"
        # Use monorepo_dir to restrict search to the frontend directory
        result: InstanceExecResponse = await task.sandbox.run_command(
            cmd, use_repo_subdir=True
        )

        raw_files: list[str] = [
            f.strip() for f in result.stdout.strip().split("\n") if f.strip()
        ]

        # Normalize all file paths to the root of the project
        all_files: list[str] = []
        for file_path in raw_files:
            normalized_path: str = await normalize_path(task, file_path)
            all_files.append(normalized_path)

        logger.info(f"Found {len(all_files)} files in the codebase")
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        all_files = []

    fuzzy_matches: dict[str, list[str]] = {}
    for pattern in patterns:
        clean_pattern: str = pattern.lstrip("./")

        logger.info(f"Looking for matches to: {clean_pattern}")

        if exact_match := [f for f in all_files if clean_pattern in f]:
            logger.info(f"Found exact match(es): {', '.join(exact_match[:3])}")
            fuzzy_matches[clean_pattern] = exact_match
            continue

        if matches := get_close_matches(clean_pattern, all_files, n=5, cutoff=0.6):
            logger.info(f"Found {len(matches)} fuzzy matches for '{clean_pattern}'")
            fuzzy_matches[clean_pattern] = matches
        else:
            # Try matching parts of the path
            parts: list[str] = clean_pattern.split("/")
            if len(parts) > 1:
                logger.info(f"Trying to match by filename: {parts[-1]}")
                if filename_matches := [f for f in all_files if parts[-1] in f]:
                    logger.info(
                        f"Found {len(filename_matches)} filename matches for '{parts[-1]}'"
                    )
                    fuzzy_matches[clean_pattern] = filename_matches
                else:
                    logger.info(f"No matches found for {clean_pattern}")
                    fuzzy_matches[clean_pattern] = []
            else:
                logger.info(f"No matches found for {clean_pattern}")
                fuzzy_matches[clean_pattern] = []

    return fuzzy_matches


def extract_top_files(
    keyword_results: dict[str, list[str]],
    fuzzy_matches: dict[str, list[str]],
    max_files: int = 10,
) -> list[str]:
    """
    Extract the top most relevant files from keyword and fuzzy search results.

    :param keyword_results: Results from keyword search
    :param fuzzy_matches: Results from fuzzy file matching
    :param max_files: Maximum number of files to return
    :return: List of top file paths
    """
    top_files: set[str] = set()

    for matched_files in fuzzy_matches.values():
        for file in matched_files[:2]:
            if file.strip():
                top_files.add(file)

    for matches in keyword_results.values():
        for match in matches[:5]:
            if match.strip():
                file_path: str = match.split(":", 1)[0]
                top_files.add(file_path)

    return list(top_files)[:max_files]


def convert_to_file_locations(
    keyword_results: dict[str, list[str]], top_files: list[str]
) -> list[FileLocation]:
    """
    Convert search results to FileLocation objects.

    :param keyword_results: Results from keyword search
    :param top_files: List of top file paths
    :return: List of FileLocation objects
    """
    file_locations: list[FileLocation] = []
    file_line_map: dict[str, set[int]] = {}

    for matches in keyword_results.values():
        for match in matches:
            parts: list[str] = match.split(":", 1)
            if len(parts) >= 2:
                file_path: str = parts[0]
                if file_path in top_files:
                    line_num: int = int(parts[1].split(":", 1)[0])
                    if file_path not in file_line_map:
                        file_line_map[file_path] = set()
                    file_line_map[file_path].add(line_num)

    for file_path, line_nums in file_line_map.items():
        if line_nums:
            min_line: int = max(1, min(line_nums) - 5)
            max_line: int = max(line_nums) + 5
            file_locations.append(
                FileLocation(path=file_path, from_line=min_line, to_line=max_line)
            )

    file_locations.extend(
        FileLocation(
            path=file_path,
            from_line=1,
            to_line=20,
        )
        for file_path in top_files
        if file_path not in file_line_map
    )
    return file_locations
