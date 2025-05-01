#!/bin/bash

echo "Monitoring containers endpoint..."
while true; do
	response=$(curl -s http://sandbox-alb-103265220.us-west-1.elb.amazonaws.com/containers/list)
	total=$(echo "${response}" | jq -r '.total_containers')
	warm=$(echo "${response}" | jq -r '.warm_containers')

	echo "$(date '+%H:%M:%S') - Total containers: ${total}, Warm containers: ${warm}"

	if [[ ${total} -gt 0 ]]; then
		echo "Container details:"
		echo "${response}" | jq -r '.containers[]'
	fi

	sleep 5
done
