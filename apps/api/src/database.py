import warnings
from typing import Any

from pymongo import MongoClient
from pymongo.results import UpdateResult
from src.config import DEV, MONGODB_URI
from src.schemas.account import User
from src.schemas.core.common import AddedRepository, Workspace
from src.utils.logging import logger

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="You appear to be connected to a CosmosDB cluster*",
)


COLLECTION_NAME: str = "speck_server_dev" if DEV else "speck_server"


class _Database:
    def __init__(self) -> None:
        self.client = MongoClient(MONGODB_URI)

        if COLLECTION_NAME not in self.client.list_database_names():
            self.db = self.client[COLLECTION_NAME]
        self.db = self.client[COLLECTION_NAME]
        collection_names: list[str] = self.db.list_collection_names()

        if "users" not in collection_names:
            self.users_collection = self.db["users"]
            self.users_collection.create_index("email", unique=True)
        if "waitlists" not in collection_names:
            self.waitlists_collection = self.db["waitlists"]
            self.waitlists_collection.create_index("email", unique=True)
        if "repos" not in collection_names:
            self.repos_collection = self.db["repos"]
            self.repos_collection.create_index("git_repo_id", unique=True)
        if "installation_ids" not in collection_names:
            self.installation_ids_collection = self.db["installation_ids"]
            self.installation_ids_collection.create_index(
                "installation_id", unique=True
            )

        self.users_collection = self.db["users"]
        self.waitlists_collection = self.db["waitlists"]
        self.repos_collection = self.db["repos"]
        self.installation_ids_collection = self.db["installation_ids"]

    def get_repo_from_task_id(
        self, user_id: str, task_id: str
    ) -> AddedRepository | None:
        repo_ids: list[int] = Database.get_user_property(user_id, "added_repos")
        repo: dict | None = Database.repos_collection.find_one(
            {
                "git_repo_id": {"$in": repo_ids},
                "tasks": {"$elemMatch": {"task_id": task_id}},
            }
        )
        return None if repo is None else AddedRepository(**repo)

    def get_repo_from_task_id_no_user(self, task_id: str) -> AddedRepository | None:
        # Bad performance use only if we don't have a user_id
        repo: dict | None = self.repos_collection.find_one(
            {
                "tasks": {"$elemMatch": {"task_id": task_id}},
            }
        )
        return None if repo is None else AddedRepository(**repo)

    def get_repo_dict(self, git_repo_id: int) -> dict | None:
        """Get the repo document from MongoDB. Returns None if not found."""
        return self.repos_collection.find_one({"git_repo_id": git_repo_id})

    def get_repo(self, git_repo_id: int) -> AddedRepository | None:
        repo_dict: dict | None = self.get_repo_dict(git_repo_id)
        return None if repo_dict is None else AddedRepository(**repo_dict)

    def get_repo_property(self, git_repo_id: int, property: str) -> Any | None:
        """Get a property from a repo document. Returns None if repo or property not found."""
        repo_dict: dict | None = self.get_repo_dict(git_repo_id)
        return None if repo_dict is None else repo_dict.get(property)

    def update_repo_property(self, git_repo_id: int, property: str, value: Any) -> None:
        """Updates a single property in a repo"""
        self.repos_collection.update_one(
            {"git_repo_id": git_repo_id},
            {"$set": {property: value}},
        )

    def get_workspace(self, git_repo_id: int, workspace_name: str) -> Workspace | None:
        repo_dict: AddedRepository | None = self.get_repo(git_repo_id)
        if repo_dict is None:
            return None
        workspace: Workspace | None = next(
            (
                workspace
                for workspace in repo_dict.workspaces
                if workspace.name == workspace_name
            ),
            None,
        )
        return workspace

    def get_workspace_property(
        self, git_repo_id: int, workspace_name: str, property: str
    ) -> Any | None:
        """Get a property from a workspace in a repo. Returns None if workspace or property not found."""
        workspace: Workspace | None = self.get_workspace(git_repo_id, workspace_name)
        return None if workspace is None else workspace.model_dump().get(property)

    def create_workspace(self, git_repo_id: int, workspace: Workspace) -> None:
        """Creates a new workspace or updates an existing one."""
        existing_repo: dict | None = self.get_repo_dict(git_repo_id)

        if existing_repo is None:
            logger.error(f"Repository with git_repo_id {git_repo_id} not found.")
            return

        existing_workspace: Workspace | None = self.get_workspace(
            git_repo_id, workspace.name
        )

        workspace_dict: dict = workspace.model_dump()

        if existing_workspace:
            self.repos_collection.update_one(
                {"git_repo_id": git_repo_id, "workspaces.name": workspace.name},
                {"$set": {"workspaces.$": workspace_dict}},
            )
        else:
            self.repos_collection.update_one(
                {"git_repo_id": git_repo_id},
                {"$push": {"workspaces": workspace_dict}},
            )

    def update_workspace_property(
        self, git_repo_id: int, workspace_name: str, property: str, value: Any
    ) -> bool:
        """Updates a single property in a space in a repo"""
        result: UpdateResult = self.repos_collection.update_one(
            {"git_repo_id": git_repo_id, "workspaces.name": workspace_name},
            {"$set": {f"workspaces.$.{property}": value}},
        )

        if result.matched_count == 0:
            logger.warning(f"Workspace not found: {git_repo_id}, {workspace_name}")
            return False

        return True

    def delete_workspace_property(
        self, git_repo_id: int, workspace_name: str, property: str
    ) -> None:
        """Deletes a single property from a space in a repo"""
        self.repos_collection.update_one(
            {"git_repo_id": git_repo_id, "workspaces.name": workspace_name},
            {"$unset": {f"workspaces.$.{property}": ""}},
        )

    def add_user(self, user: "MongoUser") -> None:
        user_dict = user.__dict__
        user_dict["added_repos"] = []
        self.users_collection.insert_one(user_dict)

    def get_user(self, id: str) -> dict:
        return self.users_collection.find_one({"id": id})

    def get_user_id_from_email(self, email: str) -> str | None:
        user: dict | None = self.users_collection.find_one({"email": email})
        return None if user is None else user["id"]

    def update_user_property(self, id: str, property: str, value: any) -> None:
        self.users_collection.update_one({"id": id}, {"$set": {property: value}})

    def get_user_property(self, id: str, property_name: str) -> Any:
        user_data: dict | None = self.users_collection.find_one({"id": id})
        return user_data.get(property_name, []) if user_data else None

    def update_user_github_settings(
        self, user_id: str, access_token: str, refresh_token: str
    ) -> None:
        self.users_collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "github_tokens.access_token": access_token,
                    "github_tokens.refresh_token": refresh_token,
                }
            },
        )


Database = _Database()


class MongoUser:
    def __init__(
        self,
        id: str,
        email: str,
        name: str,
        stripe_customer_id: str,
        user_metadata: dict[str, str],
    ):
        self.id = id
        self.email = email
        self.name = name
        self.user_metadata = user_metadata
        self.stripe_customer_id = stripe_customer_id

        self._check_exists()

    def _check_exists(self):
        """Check if the user exists in Database. If not, add them."""
        if Database.get_user(self.id) is None:
            Database.add_user(self)

    @classmethod
    def from_user(cls, user: User) -> "MongoUser":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            stripe_customer_id=user.stripe_customer_id,
            user_metadata=user.user_metadata,
        )
