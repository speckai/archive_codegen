from typing import TYPE_CHECKING
from urllib.parse import urlparse

from morphcloud.api import InstanceExecResponse
from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

# Configuration for URL path patterns
PREVIEW_PATH_PREFIX: tuple[str, int] = ("preview", 2)


def clean_route_url(route_url: str) -> str:
    """
    Cleans a route URL to get just the path portion.
    Handles both preview URLs (/preview/id1/id2/actual-path) and regular URLs.
    Ensures that leading/trailing slashes conform to Next.js route patterns.

    :param route_url: The URL to clean
    :return: Cleaned path string suitable for Next.js route matching
    """
    parsed = urlparse(route_url)
    path: str = parsed.path.rstrip("/")

    if not path:
        return "/"

    parts: list[str] = [p for p in path.split("/") if p]
    prefix: str
    skip_count: int
    prefix, skip_count = PREVIEW_PATH_PREFIX

    if len(parts) >= (1 + skip_count) and parts[0] == prefix:
        path = (
            "/" + "/".join(parts[1 + skip_count :])
            if len(parts) > (1 + skip_count)
            else "/"
        )

    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return path


async def resolve_route_file(task: "Task", route_url: str) -> str | None:
    """
    Gets the file path for a given route URL using find-route-file.

    :param task: Task object containing sandbox for command execution
    :param route_url: The URL to find the corresponding file for
    :return: Normalized file path if found, None if no file or if an error occurs
    """
    logger.debug(
        "TODO: remove this next specific processing after we take advantage of selected components"
    )
    try:
        clean_url: str = clean_route_url(route_url)

        result: InstanceExecResponse = await task.sandbox.run_command(
            f'npx --yes --package=list-routes@latest find-route-file "{clean_url}" "./"',
            use_repo_subdir=True,
        )
        if "npm error code E404" in result.stderr:
            logger.error("find-route-file is not installed")
            return None

        if "No file found for route" in result.stdout:
            return None

        file_path: str = await normalize_path(
            task, result.stdout.strip().split("\n")[-1]
        )
        if not file_path:
            logger.debug(
                f"Empty file path returned for route: {clean_url} (original: {route_url})"
            )
            return None
        return file_path

    except Exception as e:
        logger.error(f"Error finding route file for {route_url}: {str(e)}")
        return None
