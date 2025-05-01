from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from github import Github
from github.AuthenticatedUser import AuthenticatedUser
from github.NamedUser import NamedUser
from github.Organization import Organization
from src.account.security import verify_jwt_token
from src.database import Database
from src.github.utils import (
    exchange_code_for_token,
    get_github_token,
    get_github_username,
    get_issue_details,
    get_repo_branch_and_subdirectories,
    get_user_github_access_token,
)
from src.schemas.account import User
from src.schemas.github import (
    GitHubIssue,
    GitHubRepository,
    IssueDetailsResponse,
    IssueResponse,
)
from src.utils.logging import logger

router = APIRouter(prefix="/github")


@router.post("/exchange_code")
async def github_exchange_code(
    body: dict[str, str], user: User = Depends(verify_jwt_token)
):
    """
    Handles the callback from GitHub OAuth.
    """
    code: str | None = body.get("code")
    if not code:
        logger.warning("No code provided")
        return {"success": False}

    is_success: bool = await exchange_code_for_token(user.id, code)
    return {"success": is_success}


@router.get("/validate_user")
async def github_validate_user(user: User = Depends(verify_jwt_token)):
    access_token: str | None = await get_user_github_access_token(user.id)

    if not access_token:
        return {"success": False}

    username: str | None = await get_github_username(access_token)
    if not username:
        return {"success": False}

    return {"success": True, "username": username}


@router.get("/get_repo_details/{repo_id}")
async def get_repo_details(
    repo_id: int, user: User = Depends(verify_jwt_token)
) -> dict[str, Any]:
    branch_names, subdirectories = await get_repo_branch_and_subdirectories(
        repo_id, user.id
    )

    return {
        "success": True,
        "branch_names": branch_names,
        "subdirectories": subdirectories,
    }


@router.get("/authenticate")
async def authenticate(user: User = Depends(verify_jwt_token)) -> dict[str, Any]:
    if user_data := Database.users_collection.find_one({"id": user.id}):
        return (
            {"success": True}
            if user_data.get("github_installations")
            else {"success": False, "status": "NO_INSTALLATION_ID"}
        )
    else:
        return {"success": False, "message": "User not found"}


@router.get("/get_installations")
async def get_installations(user: User = Depends(verify_jwt_token)):
    user_data: dict[str, Any] = Database.users_collection.find_one({"id": user.id})
    if not user_data:
        return {"success": False, "message": "User not found"}

    github_installations: list[int] = user_data.get("github_installations", [])
    if not github_installations:
        return {"success": False, "message": "No installations found"}

    installations: list[dict[str, Any]] = list(
        Database.installation_ids_collection.find(
            {"owner_id": {"$in": github_installations}}
        )
    )

    if not installations:
        return {"success": False, "message": "No installations found"}

    installation_names: list[str] = [
        installation["account_name"] for installation in installations
    ]

    return {"success": True, "installations": installation_names}


@router.post("/refresh_installations")
async def refresh_installations(user: User = Depends(verify_jwt_token)):
    """
    Refresh the user's GitHub installations by checking for new installations
    that the user has access to but isn't yet in their github_installations array.
    """
    user_data: dict[str, Any] = Database.users_collection.find_one({"id": user.id})
    if not user_data:
        return {"success": False, "message": "User not found"}

    current_installations: list[int] = user_data.get("github_installations", [])

    access_token: str | None = await get_user_github_access_token(user.id)
    if not access_token:
        return {"success": False, "message": "User not authenticated with GitHub"}

    username: str | None = await get_github_username(access_token)
    if not username:
        return {"success": False, "message": "Failed to get GitHub username"}

    all_installations: list[dict[str, Any]] = list(
        Database.installation_ids_collection.find()
    )

    new_installations: list[int] = []
    for installation in all_installations:
        if installation["owner_id"] in current_installations:
            continue

        try:
            token: str | None = get_github_token(installation["installation_id"])

            if not token:
                continue

            github_client: Github = Github(token)

            account: AuthenticatedUser | NamedUser = github_client.get_user(
                installation["account_name"]
            )

            if account.type == "User":
                if account.login.lower() == username.lower():
                    new_installations.append(installation["owner_id"])
            else:
                try:
                    org: Organization = github_client.get_organization(
                        installation["account_name"]
                    )
                    is_member: bool = org.has_in_members(
                        github_client.get_user(username)
                    )
                    if is_member:
                        new_installations.append(installation["owner_id"])
                except Exception as e:
                    logger.error(f"Error checking org membership: {str(e)}")

        except Exception as e:
            logger.error(f"Error checking installation access: {str(e)}")

    if new_installations:
        Database.users_collection.update_one(
            {"id": user.id},
            {"$addToSet": {"github_installations": {"$each": new_installations}}},
        )

    updated_user: dict[str, Any] = Database.users_collection.find_one({"id": user.id})
    updated_installations: list[int] = updated_user.get("github_installations", [])

    installation_docs: list[dict[str, Any]] = list(
        Database.installation_ids_collection.find(
            {"owner_id": {"$in": updated_installations}}
        )
    )

    installation_names: list[str] = [doc["account_name"] for doc in installation_docs]

    return {
        "success": True,
        "installations": installation_names,
        "added_count": len(new_installations),
    }


@router.get(
    "/issue/details/{repo_id}/{issue_number}", response_model=IssueDetailsResponse
)
async def get_issue_details_endpoint(
    repo_id: int, issue_number: int, user: User = Depends(verify_jwt_token)
):
    issue_data: GitHubIssue | None = await get_issue_details(
        repo_id, issue_number, user.id
    )

    if not issue_data:
        raise HTTPException(status_code=404, detail="Issue not found")

    repository: GitHubRepository = GitHubRepository(
        id=issue_data.repository_id,
        name=issue_data.repository_name,
        owner=issue_data.repository_owner,
    )

    issue_response: IssueResponse = IssueResponse(
        title=issue_data.title,
        description=issue_data.body,
        number=issue_data.number,
        state=issue_data.state,
        url=issue_data.html_url,
        repository=repository,
    )

    return IssueDetailsResponse(success=True, issue=issue_response)
