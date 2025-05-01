#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get outputs from terraform
echo -e "${YELLOW}Getting service information...${NC}"
SERVICE_NAME=$(tofu output -raw manager_service_name)
CLUSTER_NAME=$(tofu output -raw cluster_name)
ALB_DNS=$(tofu output -raw manager_alb_dns)

echo -e "${GREEN}ALB DNS:${NC} http://${ALB_DNS}"

# Get task ARN
echo -e "\n${YELLOW}Getting task information...${NC}"
TASK_ARN=$(aws ecs list-tasks --cluster "${CLUSTER_NAME}" --service-name "${SERVICE_NAME}" --query 'taskArns[0]' --output text)

if [[ ${TASK_ARN} != "None" ]]; then
	# Get private IP
	PRIVATE_IP=$(aws ecs describe-tasks --cluster "${CLUSTER_NAME}" --tasks "${TASK_ARN}" --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' --output text)
	echo -e "${GREEN}Manager Private IP:${NC} ${PRIVATE_IP}"
else
	echo -e "${YELLOW}No tasks found running for the manager service${NC}"
fi
