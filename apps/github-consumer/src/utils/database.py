import warnings

from pymongo import MongoClient
from src.config import DEV, MONGODB_URI

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

        self.users_collection = self.db["users"]
        self.repos_collection = self.db["repos"]
        self.installation_ids_collection = self.db["installation_ids"]


Database: _Database = _Database()
