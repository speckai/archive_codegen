import time
from datetime import datetime, timezone

import httpx
import requests

# import tracemalloc
from github import Github, GithubException
from github.AuthenticatedUser import AuthenticatedUser
from github.Branch import Branch
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.NamedUser import NamedUser
from github.Repository import Repository
from jwt import encode
from src.config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_PRIVATE_KEY,
    GITHUB_REDIRECT_URI,
)
from src.database import Database
from src.schemas.core.common import AddedRepository
from src.schemas.github import GitHubComment, GitHubIssue, GitHubLabel, GitHubUser
from src.utils.logging import logger

token_cache: dict[str, str] = {}


async def get_repo_data_from_id(git_repo_id: int, user_id: str) -> dict | None:
    access_token: str | None = await get_user_github_access_token(user_id)
    if not access_token:
        return None

    github_client: Github = Github(access_token)
    try:
        repo: Repository = github_client.get_repo(git_repo_id)
        owner = repo.owner
        owner_data: dict = {
            "name": owner.login,
            "url": owner.html_url,
            "avatar_url": owner.avatar_url,
            "id": owner.id,
        }
        repo_data: dict = {
            "name": repo.name,
            "full_name": repo.full_name,
            "url": repo.html_url,
            "visibility": repo.visibility,
            "owner": owner_data,
        }

        return repo_data

    except GithubException as e:
        logger.error(f"Failed to get repository data: {str(e)}")
        return None
    finally:
        github_client.close()


def get_repo_installation_id(git_repo_id: int, user_id: str) -> str:
    user_data: dict = Database.users_collection.find_one({"id": user_id})
    if not user_data:
        raise ValueError("User not found in database")

    repo: AddedRepository | None = Database.get_repo(git_repo_id)
    if not repo:
        raise ValueError("Repo not found in database")

    repo_owner_id: int = repo.owner["id"]

    github_installations: list[int] = user_data.get("github_installations", [])
    if repo_owner_id not in github_installations:
        raise ValueError("Github installation ID not found for this user")

    installation = Database.installation_ids_collection.find_one(
        {"owner_id": repo_owner_id}
    )
    if not installation:
        raise ValueError("Github installation ID not found in database")

    return installation["installation_id"]


def get_installation_id_from_owner(repo_owner_id: int) -> str:
    installation: dict | None = Database.installation_ids_collection.find_one(
        {"owner_id": repo_owner_id}
    )
    if not installation:
        raise ValueError("Github installation ID not found in database")

    return installation["installation_id"]


def get_installed_repos(
    user_id: str,
) -> dict[str, list[dict[str, str | int]] | list[str]]:
    """Get the installed repos"""
    user_data: dict = Database.users_collection.find_one(
        {"id": user_id}, {"github_installations": 1}
    )

    owner_ids: list[int] = user_data.get("github_installations", [])
    installations = list(
        Database.installation_ids_collection.find({"owner_id": {"$in": owner_ids}})
    )

    installation_ids: list[dict[str, str]] = [
        {
            "id": installation["installation_id"],
            "name": installation["account_name"],
        }
        for installation in installations
    ]

    installed_repos: list = []
    existing_repos: list = []
    failed_installations: list[dict[str, str]] = []
    for installation in installation_ids:
        token: str | None = get_github_token(installation["id"])
        if not token:
            failed_installations.append(
                {"id": installation["id"], "name": installation["name"]}
            )
            continue

        headers: dict = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        all_repositories: list = []
        page: int = 1
        max_pages: int = 10

        while page <= max_pages:
            response: requests.Response = requests.get(
                f"https://api.github.com/installation/repositories?per_page=100&page={page}",
                headers=headers,
            )
            if response.status_code != 200:
                raise GithubException(
                    f"Request failed with status {response.status_code}."
                )

            data: dict = response.json()
            repositories: list = data.get("repositories", [])
            if not repositories:
                break

            all_repositories.extend(repositories)
            page += 1

        if page > max_pages:
            logger.warning(
                f"Hit the max number of pages ({max_pages}) while fetching repositories"
            )

        added_repos: list[str] = Database.get_user_property(user_id, "added_repos")
        added_repo_ids: set = set(added_repos)

        for repo in all_repositories:
            if repo.get("id") in added_repo_ids:
                existing_repos.append(repo.get("name"))
                continue

            owner_data: dict = repo.get("owner")

            updated_at_str: str = repo.get("updated_at")
            updated_at_datetime: datetime = datetime.strptime(
                updated_at_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            seconds_from_unix: int = int(updated_at_datetime.timestamp())

            installed_repos.append(
                {
                    "git_repo_id": repo.get("id"),
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "url": repo.get("html_url"),
                    "owner": {
                        "avatar_url": owner_data.get("avatar_url"),
                        "name": owner_data.get("login"),
                        "url": owner_data.get("html_url"),
                        "id": owner_data.get("id"),
                    },
                    "visibility": repo.get("visibility"),
                    "updated_at": seconds_from_unix,
                }
            )
    return {
        "installed_repos": installed_repos,
        "failed_installations": failed_installations,
        "existing_repos": existing_repos,
    }


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

    token_cache[installation_id] = token
    return token


def get_github_user_object(access_token: str) -> AuthenticatedUser | None:
    try:
        github_client = Github(access_token)
        return github_client.get_user()
    except Exception as _e:
        return None


def get_installation_ids(user_id: str) -> list[dict[str, str]]:
    """Get the installation ids and names for GitHub organizations"""
    user_data = Database.users_collection.find_one(
        {"id": user_id}, {"github_installations": 1}
    )
    if not user_data:
        return []

    owner_ids: list[int] = user_data.get("github_installations", [])
    installations = list(
        Database.installation_ids_collection.find({"owner_id": {"$in": owner_ids}})
    )

    org_installations: list[dict[str, str]] = []
    for installation in installations:
        jwt: str = _create_jwt(
            client_id=GITHUB_CLIENT_ID, private_key=GITHUB_PRIVATE_KEY
        )
        token: str | None = _get_token(
            installation_id=installation["installation_id"], jwt=jwt
        )
        if not token:
            continue

        github_client: Github = Github(token)
        try:
            account = github_client.get_user(installation["account_name"])
            if account.type == "Organization":
                org_installations.append(
                    {
                        "name": installation["account_name"],
                        "id": installation["installation_id"],
                    }
                )
        except Exception as _e:
            continue

    return org_installations


async def get_github_username(access_token: str) -> str | None:
    username: str | None = None
    try:
        github_client = Github(access_token)
        user = github_client.get_user()
        username = user.login
    except Exception as _e:
        return None
    return username


async def get_github_token_from_repo(repo_id: int, user_id: str) -> str | None:
    installation_id: str | None = get_repo_installation_id(repo_id, user_id)
    if not installation_id:
        return None

    token: str | None = get_github_token(installation_id)
    return token


async def get_user_github_access_token(user_id: str) -> str | None:
    user_data: dict | None = Database.users_collection.find_one({"id": user_id})
    if not user_data:
        logger.error(f"User not found in database: {user_id}")
        return None

    github_settings: dict = user_data.get("github_tokens", {})
    refresh_token: str | None = github_settings.get("refresh_token")
    if not refresh_token:
        return None

    access_token: str | None = github_settings.get("access_token")
    if not access_token:
        return None

    github_client: Github = Github(access_token)
    try:
        user: AuthenticatedUser | NamedUser = github_client.get_user()
        _ = user.login

        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        return access_token
    except GithubException as e:
        if e.status in [401]:  # Bad credentials
            headers = {
                "Accept": "application/json",
            }

            params = {
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
            response = requests.post(
                "https://github.com/login/oauth/access_token",
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                new_tokens = response.json()
                new_access_token = new_tokens.get("access_token")
                new_refresh_token = new_tokens.get("refresh_token")
                if not new_access_token or not new_refresh_token:
                    logger.error("Failed to refresh GitHub token")
                    return None

                Database.update_user_github_settings(
                    user_id, new_access_token, new_refresh_token
                )
                return new_access_token

        return None


async def exchange_code_for_token(user_id: str, code: str) -> bool:
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        token_data: dict[str, str] = token_response.json()

    access_token: str | None = token_data.get("access_token")
    refresh_token: str | None = token_data.get("refresh_token")

    if not access_token or not refresh_token:
        logger.warning("No access token provided")
        return False

    github_user_object: AuthenticatedUser | None = get_github_user_object(access_token)
    if not github_user_object:
        logger.warning("Failed to get GitHub user object")
        return False

    github_user_id: int = github_user_object.id
    if not github_user_id:
        logger.warning(f"Failed to get GitHub user id - {github_user_id}")
        return False

    Database.update_user_github_settings(user_id, access_token, refresh_token)
    Database.update_user_property(user_id, "github_user_id", github_user_id)
    return True


async def get_issue_details(
    repo_id: int, issue_number: int, user_id: str
) -> GitHubIssue | None:
    """
    Get details of a GitHub issue

    :param issue_id_param: The parameter in format "repo_id/issue_number" where issue_number is the # displayed in GitHub UI
    :param user_id: The user ID
    :return: GitHubIssue object or None if issue not found
    """
    try:
        try:
            logger.info(f"Fetching issue #{issue_number} from repository {repo_id}")
        except ValueError as e:
            logger.error(
                f"Invalid format: {issue_number}. Expected 'repo_id/issue_number'. Error: {str(e)}"
            )
            return None

        access_token: str | None = await get_user_github_access_token(user_id)
        if not access_token:
            logger.error(f"Failed to get GitHub access token for user {user_id}")
            return None

        github_client: Github = Github(access_token)

        try:
            try:
                repo: Repository = github_client.get_repo(repo_id)
                logger.info(f"Found repository: {repo.full_name} (ID: {repo.id})")
            except GithubException as e:
                logger.error(f"Repository not found: {repo_id}. Error: {str(e)}")
                return None

            try:
                issue: Issue = repo.get_issue(issue_number)
                logger.info(f"Found issue: #{issue.number} - {issue.title}")
            except GithubException as e:
                logger.error(
                    f"Issue #{issue_number} not found in repository {repo.full_name}. Error: {str(e)}"
                )
                return None
            user_data = GitHubUser(
                id=issue.user.id,
                login=issue.user.login,
                avatar_url=issue.user.avatar_url,
                html_url=issue.user.html_url,
            )
            assignees: list[GitHubUser] = []
            assignees.extend(
                GitHubUser(
                    id=assignee.id,
                    login=assignee.login,
                    avatar_url=assignee.avatar_url,
                    html_url=assignee.html_url,
                )
                for assignee in issue.assignees
            )

            labels: list[GitHubLabel] = []
            labels.extend(
                GitHubLabel(
                    id=label.id,
                    name=label.name,
                    color=label.color,
                    description=label.description,
                )
                for label in issue.labels
            )

            comments: list[GitHubComment] = []
            for comment in issue.get_comments():
                comment_user = GitHubUser(
                    id=comment.user.id,
                    login=comment.user.login,
                    avatar_url=comment.user.avatar_url,
                    html_url=comment.user.html_url,
                )
                comments.append(
                    GitHubComment(
                        id=comment.id,
                        user=comment_user,
                        body=comment.body,
                        created_at=comment.created_at,
                        updated_at=comment.updated_at,
                        html_url=comment.html_url,
                    )
                )

            return GitHubIssue(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                html_url=issue.html_url,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                closed_at=issue.closed_at,
                user=user_data,
                assignees=assignees,
                labels=labels,
                comments=comments,
                repository_id=repo.id,
                repository_name=repo.name,
                repository_owner=repo.owner.login,
            )
        except GithubException as e:
            logger.error(f"GitHub API error: {str(e)}")
            return None
        finally:
            github_client.close()

    except Exception as e:
        logger.error(f"Error getting issue details: {str(e)}")
        return None


async def create_issue(
    repo_id: int,
    title: str,
    body: str,
    user_id: str,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> GitHubIssue | None:
    """
    Create a new issue in the specified GitHub repository.

    :param repo_id: The ID of the GitHub repository
    :param title: The title of the issue
    :param body: The body/description of the issue
    :param user_id: The ID of the user creating the issue
    :param labels: Optional list of label names to add to the issue
    :param assignees: Optional list of GitHub usernames to assign to the issue
    :return: GitHubIssue object if successful, None otherwise
    """
    try:
        access_token: str | None = await get_github_token_from_repo(repo_id, user_id)
        if not access_token:
            logger.error(f"Failed to get GitHub access token for user {user_id}")
            return None

        github_client: Github = Github(access_token)
        try:
            repo: Repository = github_client.get_repo(repo_id)
            logger.info(f"Found repository: {repo.full_name}")

            try:
                issue: Issue = repo.create_issue(
                    title=title,
                    body=body,
                    labels=labels or [],
                    assignees=assignees or [],
                )
                logger.info(f"Created issue: #{issue.number} - {issue.title}")

                user_data: GitHubUser = GitHubUser(
                    id=issue.user.id,
                    login=issue.user.login,
                    avatar_url=issue.user.avatar_url,
                    html_url=issue.user.html_url,
                )

                return GitHubIssue(
                    id=issue.id,
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    state=issue.state,
                    html_url=issue.html_url,
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    user=user_data,
                    assignees=[],
                    labels=[],
                    comments=[],
                    repository_id=repo.id,
                    repository_name=repo.name,
                    repository_owner=repo.owner.login,
                )

            except GithubException as e:
                logger.error(f"Failed to create issue: {str(e)}")
                return None

        except GithubException as e:
            logger.error(f"Repository not found: {repo_id}. Error: {str(e)}")
            return None
        finally:
            github_client.close()

    except Exception as e:
        logger.error(f"Error creating issue: {str(e)}")
        return None


async def create_issue_comment(
    repo_id: int,
    issue_number: int,
    comment_text: str,
    user_id: str,
) -> GitHubComment | None:
    """
    Create a comment on a GitHub issue.

    :param repo_id: The ID of the GitHub repository
    :param issue_number: The issue number to comment on
    :param comment_text: The text content of the comment
    :param user_id: The ID of the user creating the comment
    :return: GitHubComment object if successful, None otherwise
    """
    try:
        access_token: str | None = await get_github_token_from_repo(repo_id, user_id)
        if not access_token:
            logger.error(f"Failed to get GitHub access token for user {user_id}")
            return None

        github_client: Github = Github(access_token)
        try:
            repo: Repository = github_client.get_repo(repo_id)
            logger.info(f"Found repository: {repo.full_name}")

            try:
                issue: Issue = repo.get_issue(issue_number)
                logger.info(f"Found issue: #{issue.number} - {issue.title}")

                comment: IssueComment = issue.create_comment(comment_text)
                logger.info(f"Created comment on issue #{issue.number}")

                comment_user = GitHubUser(
                    id=comment.user.id,
                    login=comment.user.login,
                    avatar_url=comment.user.avatar_url,
                    html_url=comment.user.html_url,
                )

                return GitHubComment(
                    id=comment.id,
                    user=comment_user,
                    body=comment.body,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    html_url=comment.html_url,
                )

            except GithubException as e:
                logger.error(f"Failed to create comment: {str(e)}")
                return None

        except GithubException as e:
            logger.error(f"Repository not found: {repo_id}. Error: {str(e)}")
            return None
        finally:
            github_client.close()

    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return None


async def get_repo_branch_and_subdirectories(
    repo_id: int, user_id: str
) -> tuple[list[str], list[str]]:
    access_token: str | None = await get_github_token_from_repo(repo_id, user_id)
    if not access_token:
        logger.error(f"Failed to get GitHub access token for user {user_id}")
        return None

    github_client: Github = Github(access_token)
    try:
        repo: Repository = github_client.get_repo(repo_id)
        logger.info(f"Found repository: {repo.full_name}")
    except GithubException as e:
        logger.error(f"Repository not found: {repo_id}. Error: {str(e)}")
        return None

    branches: list[Branch] = repo.get_branches()
    branch_names: list[str] = [branch.name for branch in branches]

    subdirectories: set[str] = set()
    try:
        contents = repo.get_git_tree("HEAD", recursive=True)
        for item in contents.tree:
            if item.path.endswith("package.json") and "/" in item.path:
                directory = "/".join(item.path.split("/")[:-1])
                subdirectories.add(directory)
    except GithubException as e:
        logger.error(f"Error finding subdirectories: {str(e)}")

    if "/" not in subdirectories:
        subdirectories.add("/")

    return branch_names, list(subdirectories)
