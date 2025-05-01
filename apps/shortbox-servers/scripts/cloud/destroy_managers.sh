#!/bin/bash

TASKS=$(aws ecs list-tasks --cluster sandbox-cluster --no-cli-pager | jq -r '.taskArns[]')

for task_arn in ${TASKS}; do
	task_id=$(echo "${task_arn}" | awk -F'/' '{print $3}')

	task_info=$(aws ecs describe-tasks --cluster sandbox-cluster --tasks "${task_arn}" --no-cli-pager)

	group=$(echo "${task_info}" | jq -r '.tasks[0].group')

	if [[ ${group} == "service:sandbox-manager" ]]; then
		echo "Stopping manager task: ${task_id}"
		aws ecs stop-task --cluster sandbox-cluster --task "${task_id}" --no-cli-pager
	else
		echo "Skipping task: ${task_id} (group: ${group})"
	fi
done

echo "All manager tasks have been stopped. Container task(s) are preserved."
