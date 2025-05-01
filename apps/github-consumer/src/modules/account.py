from typing import Any

from loguru import logger
from src.utils.database import Database


def _delete_installation(owner_id: int) -> bool:
    """Deletes an installation from the installation_ids collection"""
    Database.installation_ids_collection.delete_one({"owner_id": owner_id})

    Database.users_collection.update_many(
        {"github_installations": owner_id},
        {"$pull": {"github_installations": owner_id}},
    )

    return True


def _upsert_installation(
    installation_id: int,
    owner_id: int,
    account_name: str,
) -> bool:
    """Upserts installation to the installation_ids collection"""
    Database.installation_ids_collection.update_one(
        {"owner_id": owner_id},
        {
            "$set": {
                "installation_id": installation_id,
                "account_name": account_name,
            }
        },
        upsert=True,
    )
    return True


def _add_installation_to_user(
    user_id: str,
    owner_id: int,
) -> bool:
    """Adds installation to a user's github_installations array if not already present"""
    if Database.users_collection.find_one(
        {
            "id": user_id,
            "github_installations": owner_id,
        }
    ):
        logger.warning(
            f"Installation for owner {owner_id} already exists for user {user_id}"
        )
        return True

    logger.warning(f"Adding installation {owner_id} to user {user_id}")
    Database.users_collection.update_one(
        {"id": user_id},
        {"$addToSet": {"github_installations": owner_id}},
    )
    return True


async def handle_installation(body: dict[str, Any]) -> dict[str, Any]:
    action: str = body.get("action")
    installation: dict[str, any] = body.get("installation")
    installation_id: int = installation.get("id")

    account: dict[str, any] = installation.get("account")
    account_id: int = account.get("id")
    account_login: str = account.get("login")

    sender: dict[str, any] = body.get("sender")
    sender_id: str = sender.get("id")

    user: dict[str, Any] | None = Database.users_collection.find_one(
        {"github_user_id": sender_id}
    )
    if not user:
        logger.error(f"User not found for sender_id {sender_id}")
        return {"success": False}

    user_id: str = user.get("id")

    if action == "deleted":
        _delete_installation(account_id)
        logger.info(
            f"Deleted installation {installation_id} for account {account_login} ({account_id})"
        )
    elif action == "created":
        if user_id:
            _upsert_installation(installation_id, account_id, account_login)
            _add_installation_to_user(user_id, account_id)
            logger.info(
                f"Created installation {installation_id} for account {account_login} ({account_id})"
            )
        else:
            logger.error("User not found for installation id")

    logger.info(f"Found user_id: {user_id}")

    return {"success": True}
