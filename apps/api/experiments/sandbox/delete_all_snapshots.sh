#!/bin/bash

# Get all snapshot IDs
SNAPSHOT_IDS=$(morphcloud snapshot list | grep 'snapshot_' | awk '{print $1}')

# Loop through each ID and delete it
for ID in $SNAPSHOT_IDS; do
	echo "Deleting snapshot $ID..."
	morphcloud snapshot delete $ID
done

echo "All snapshots deleted."
