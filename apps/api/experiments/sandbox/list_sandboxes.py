from morphcloud.api import MorphCloudClient
from src.config import MORPHCLOUD_API_KEY

client = MorphCloudClient(MORPHCLOUD_API_KEY)

# List all snapshots
snapshots = client.snapshots.list()

for snapshot in snapshots:
    print(f"ID: {snapshot.id}, Created At: {snapshot.created}")
