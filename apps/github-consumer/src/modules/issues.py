import time
from typing import Any

import requests
from jwt import encode
from loguru import logger
from pymongo.results import UpdateResult
from src.config import DEV, GITHUB_CLIENT_ID, GITHUB_PRIVATE_KEY
from src.utils.database import Database

ENDPOINT: str = "http://localhost:3000/home" if DEV else "https://speck.sh/home"


def _create_jwt(client_id: str, private_key: str) -> str:
    """Create a JWT"""
    now: int = int(time.time())
    ten_mins_from_now: int = now + (60 * 10) - 20  # 20 seconds off for buffer
    payload: dict = {
        "iat": now,
        "exp": ten_mins_from_now,
        "iss": client_id,
    }

    try:
        return encode(payload, private_key, algorithm="RS256")
    except Exception as e:
        logger.error(f"Failed to create JWT: {e}")
        logger.warning(f"Client ID: {GITHUB_CLIENT_ID}")
        logger.warning(f"Private Key: \n\n{GITHUB_PRIVATE_KEY}\n\n")
        raise e


def _get_token(installation_id: str, jwt: str) -> str | None:
    """Get a token"""
    headers: dict = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {jwt}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response: requests.Response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers,
    )

    if "token" not in response.json():
        logger.error(f"Failed to get token for installation {installation_id}")
        logger.error(response.json())
        return None

    return response.json()["token"]


def get_github_token(installation_id: str) -> str | None:
    """
    Get a GitHub token
    :param user_id: The user id
    :return: The GitHub token
    """
    jwt: str = _create_jwt(client_id=GITHUB_CLIENT_ID, private_key=GITHUB_PRIVATE_KEY)
    token: str | None = _get_token(installation_id=installation_id, jwt=jwt)
    if not token:
        logger.error("Invalid Git token")
        return None
    return token


def is_frontend_scoped(issue_title: str, issue_body: str) -> bool:
    return True


async def handle_issue_comment(body: dict[str, Any]) -> dict[str, Any]:
    comment: dict[str, Any] = body.get("comment", {})
    comment_content: str = comment.get("body")
    if "@speck" not in comment_content.lower():
        return {"success": True}

    issue: dict[str, Any] = body.get("issue", {})
    issue.get("id")

    comment_user: dict[str, Any] = comment.get("user", {})
    comment_user_id: str = comment_user.get("id")
    comment.get("id")

    if "speck-" in comment_user.get("login"):
        return {"success": True}

    installation: dict[str, Any] = body.get("installation", {})
    installation_id: int = installation.get("id")

    issue_html_url: str = issue.get("html_url")
    issue_title: str = issue.get("title")
    issue_body: str = issue.get("body")

    repository: dict[str, Any] = body.get("repository", {})
    repository_id: str = repository.get("id")

    installation: dict[str, Any] = body.get("installation", {})
    installation_id: int = installation.get("id")

    comments_url: str = issue.get("comments_url")

    token: str | None = get_github_token(str(installation_id))
    if not token:
        logger.error("Failed to get GitHub token")
        return {"success": False}

    headers: dict = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    all_comments: list[dict[str, Any]] = []
    try:
        response: requests.Response = requests.get(comments_url, headers=headers)
        response.raise_for_status()
        all_comments: list[dict[str, Any]] = response.json()

    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}")
        return {"success": False}

    processed_comments: list[dict[str, Any]] = []
    for comment in all_comments:
        processed_comment: dict[str, Any] = {
            "id": comment.get("id"),
            "user": {
                "login": comment.get("user", {}).get("login"),
                "id": comment.get("user", {}).get("id"),
            },
            "body": comment.get("body"),
        }
        processed_comments.append(processed_comment)

    quote_lines: list[str] = [f"> {line}" for line in comment_content.split("\n")]
    quote_text: str = "\n".join(quote_lines)

    comment_body: str = f"""
Mention details:
Repo: {repository_id}
Issue URL: {issue_html_url}
Comment body: {comment_content}
Comment URL: {comment_user_id}
Title: {issue_title}
Body: {issue_body}
Number of comments: {len(processed_comments)}
"""
    post_body: str = f"{quote_text}\n\n{comment_body}" if quote_text else comment_body

    try:
        response: requests.Response = requests.post(
            comments_url, headers=headers, json={"body": post_body}
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to post quote reply: {e}")
        return {"success": False}

    return {"success": True}


async def handle_new_issue(body: dict[str, Any]) -> dict[str, Any]:
    repository: dict[str, Any] = body.get("repository", {})
    repository_id: str = repository.get("id")
    repository_name: str = repository.get("full_name")

    issue: dict[str, Any] = body.get("issue", {})
    issue_number: int = issue.get("number")
    issue_title: str = issue.get("title")
    issue_body: str = issue.get("body", "")
    issue_id: str = str(issue.get("id"))
    comments_url: str = issue.get("comments_url")

    repo_installation: dict[str, Any] | None = Database.repos_collection.find_one(
        {"git_repo_id": repository_id}
    )
    if not repo_installation:
        logger.error(
            f"Repository {repository_name} ({repository_id}) not found in database"
        )
        return {"success": False}

    installation: dict[str, Any] = body.get("installation", {})
    installation_id: int = installation.get("id")

    token: str | None = get_github_token(str(installation_id))
    if not token:
        logger.error("Failed to get GitHub token")
        return {"success": False}

    headers: dict = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    speck_url: str = f"{ENDPOINT}?repo_id={repository_id}&issue_number={issue_number}"

    is_frontend: bool = is_frontend_scoped(issue_title, issue_body)
    logger.info(f"Issue {issue_id} classified as frontend: {is_frontend}")

    comment_body: str = (
        f"You can view and work on this issue in Speck by clicking here: [Open in Speck]({speck_url})"
    )

    try:
        response: requests.Response = requests.post(
            comments_url, headers=headers, json={"body": comment_body}
        )
        response.raise_for_status()
        logger.info(f"Successfully posted comment to issue {issue_id}")
    except Exception as e:
        logger.error(f"Failed to post comment: {e}")
        return {"success": False}

    return {"success": True}


async def handle_issue_closed(body: dict[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = body.get("issue", {})
    issue_number: int = issue.get("number")

    action: str = body.get("action")
    is_deleted: bool = action == "deleted"
    is_reopened: bool = action == "reopened"

    repository: dict[str, Any] = body.get("repository", {})
    repository_id: str = repository.get("id")
    repository_name: str = repository.get("full_name")

    logger.info(f"Processing issue #{issue_number} {action} for repo {repository_name}")

    repo_installation: dict[str, Any] | None = Database.repos_collection.find_one(
        {"git_repo_id": repository_id}
    )

    if not repo_installation:
        logger.error(
            f"Repository {repository_name} ({repository_id}) not found in database"
        )
        return {"success": False}

    if is_deleted:
        update_operation = {
            "$unset": {"tasks.$.issue_number": "", "tasks.$.issue_closed": ""}
        }
        log_message = f"Removed issue references for deleted issue #{issue_number}"
    elif is_reopened:
        update_operation = {"$set": {"tasks.$.issue_closed": False}}
        log_message = f"Marked issue #{issue_number} as reopened"
    else:
        update_operation = {"$set": {"tasks.$.issue_closed": True}}
        log_message = f"Marked issue #{issue_number} as closed"

    result: UpdateResult = Database.repos_collection.update_one(
        {
            "git_repo_id": repository_id,
            "tasks": {"$elemMatch": {"issue_number": issue_number}},
        },
        update_operation,
    )

    if result.modified_count > 0:
        logger.info(f"Updated {result.modified_count} tasks: {log_message}")
    else:
        logger.info(
            f"No tasks found for issue #{issue_number} in repository {repository_name}"
        )

    return {"success": True}


async def handle_pr_status_change(body: dict[str, Any]) -> dict[str, Any]:
    pull_request: dict[str, Any] = body.get("pull_request", {})
    pr_number: int = pull_request.get("number")
    is_merged: bool = pull_request.get("merged", False)
    action: str = body.get("action")

    if action == "reopened":
        new_status: str = "pr_open"
    else:
        new_status: str = "pr_merged" if is_merged else "pr_closed"

    repository: dict[str, Any] = body.get("repository", {})
    repository_id: str = repository.get("id")
    repository_name: str = repository.get("full_name")

    logger.info(
        f"Processing PR #{pr_number} status change to {new_status} for repo {repository_name}"
    )

    repo_installation: dict[str, Any] | None = Database.repos_collection.find_one(
        {"git_repo_id": repository_id}
    )

    if not repo_installation:
        logger.error(
            f"Repository {repository_name} ({repository_id}) not found in database"
        )
        return {"success": False}

    if action == "reopened":
        query_match = {
            "$elemMatch": {
                "pr_number": pr_number,
                "task_state": {"$in": ["pr_closed", "pr_merged"]},
            }
        }
    else:
        query_match = {
            "$elemMatch": {
                "pr_number": pr_number,
                "task_state": "pr_open",
            }
        }

    result = Database.repos_collection.update_one(
        {"git_repo_id": repository_id, "tasks": query_match},
        {"$set": {"tasks.$.task_state": new_status}},
    )

    if result.modified_count > 0:
        logger.info(
            f"Updated {result.modified_count} tasks for PR #{pr_number} to status: {new_status}"
        )
    else:
        logger.info(
            f"No tasks found for PR #{pr_number} in repository {repository_name}"
        )

    return {"success": True}
