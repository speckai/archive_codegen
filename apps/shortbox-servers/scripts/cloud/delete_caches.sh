#!/bin/bash
BASE_URL="http://sandbox-alb-103265220.us-west-1.elb.amazonaws.com"

# Function to URL encode strings
urlencode() {
	python3 -c "import urllib.parse; print(urllib.parse.quote('$1'))"
}

# Get the list of caches in JSON format
cache_list_json=$(curl -s "${BASE_URL}/dir_cache/list")

# Extract the cache names using jq
cache_names=$(echo "${cache_list_json}" | jq -r '.caches[].name')

# Iterate over the cache names and delete each cache
while IFS= read -r cache_name; do
	echo "Deleting cache: ${cache_name}"
	# URL encode the cache name before using it in the URL
	encoded_name=$(urlencode "${cache_name}")
	curl -s -X DELETE "${BASE_URL}/dir_cache/delete/${encoded_name}"
	echo
done <<<"${cache_names}"

echo "Checking remaining caches:"
curl -s "${BASE_URL}/dir_cache/list"
