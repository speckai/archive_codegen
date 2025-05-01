import asyncio
import json
import os
import time
import traceback

import aioboto3
import aiohttp
from loguru import logger
from src.manager.container_cache import container_cache
from src.manager.manager_watchdog import MIN_WARM_CONTAINERS, ManagerWatchdog
from src.schemas import ContainerInfo

HEALTH_CHECK_TIMEOUT_SECONDS: int = 10  # Each container health check attempt
CONTAINER_PORT: int = 8000  # Default container port
ECS_STOP_WAIT_RETRIES: int = 30  # Number of retries when stopping container

AWS_PRIVATE_IP_PREFIX: str = "10."
AWS_ENI_TYPE: str = "ElasticNetworkInterface"
AWS_ENI_ID_KEY: str = "networkInterfaceId"


class ContainerManager:
    def __init__(
        self,
        cluster_name: str,
        task_definition: str,
        subnet_ids: list[str],
        security_group_id: str,
        efs_filesystem_id: str = "",
        is_local: bool = False,
    ):
        self.cluster_name: str = cluster_name
        self.task_definition: str = task_definition
        self.subnet_ids: list[str] = subnet_ids
        self.security_group_id: str = security_group_id
        self.efs_filesystem_id: str = efs_filesystem_id
        self.is_local: bool = is_local

        self.session = aioboto3.Session()
        self.ecs: aioboto3.client | None = None
        self.ec2: aioboto3.client | None = None

        self.watchdog: ManagerWatchdog = ManagerWatchdog(self)

    async def initialize_clients(self):
        """Initialize AWS clients if not in local mode."""
        if not self.is_local:
            self.ecs = await self.session.client("ecs").__aenter__()
            self.ec2 = await self.session.client("ec2").__aenter__()

    async def cleanup_clients(self):
        """Cleanup AWS clients."""
        if not self.is_local:
            if self.ecs:
                await self.ecs.__aexit__(None, None, None)
            if self.ec2:
                await self.ec2.__aexit__(None, None, None)

    async def check_container_health(
        self, task_id: str, container_ip: str, startup_grace_period: bool = False
    ) -> tuple[bool, float | None]:
        """
        Checks if a container is healthy by hitting its /health endpoint.
        """
        if not container_ip:
            logger.warning(f"Cannot check health for task_id={task_id} - missing IP!")
            return False, None

        ips_to_try: list[str] = await self._get_public_ip_for_task(
            task_id, container_ip
        )
        timeout: int = (
            HEALTH_CHECK_TIMEOUT_SECONDS * 2
            if startup_grace_period
            else HEALTH_CHECK_TIMEOUT_SECONDS
        )
        max_retries: int = 2 if startup_grace_period else 1
        last_error: Exception | None = None

        for ip in ips_to_try:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        await asyncio.sleep(2**attempt)

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"http://{ip}:{CONTAINER_PORT}/health", timeout=timeout
                        ) as response:
                            if response.status == 200:
                                health_data = await response.json()
                                is_healthy = health_data.get("status") == "healthy"
                                last_disconnect = health_data.get("last_disconnect", 0)

                                if last_disconnect > 0:
                                    return is_healthy, last_disconnect

                                return is_healthy, None

                except Exception as e:
                    last_error = e
                    continue

        logger.warning(
            f"All health checks failed for task_id={task_id}, error={last_error}"
        )
        return False, time.time()

    async def cleanup_container(self, task_id: str) -> None:
        logger.info(f"Requesting cleanup of container with task_id={task_id}")
        if self.is_local:
            logger.info(
                f"Running in local mode, ignoring ECS stop for task_id={task_id}"
            )
            return

        try:
            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name, tasks=[task_id]
            )
            tasks: list[dict] = task_details["tasks"]
            if not tasks:
                logger.info(
                    f"Task {task_id} not found in ECS, likely already cleaned up"
                )
                return

            task: dict = tasks[0]
            if task["lastStatus"] in ["STOPPED", "STOPPING"]:
                logger.info(
                    f"Task {task_id} already stopping or stopped, skipping further cleanup"
                )
                return

            logger.info(f"Stopping ECS task {task_id}")
            await self.ecs.stop_task(
                cluster=self.cluster_name,
                task=task_id,
                reason="Shortbox container manager cleanup",
            )

            for _ in range(ECS_STOP_WAIT_RETRIES):
                task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                    cluster=self.cluster_name, tasks=[task_id]
                )
                tasks: list[dict] = task_details["tasks"]
                if not tasks:
                    logger.info(f"Task {task_id} removed from the cluster")
                    return

                task: dict = tasks[0]
                if task["lastStatus"] == "STOPPED":
                    logger.info(f"Task {task_id} successfully stopped")
                    return

                await asyncio.sleep(1)

            logger.warning(f"Task {task_id} did not reach STOPPED state within timeout")

        except Exception as e:
            logger.error(f"Error during cleanup of container {task_id}: {e}")
            logger.error(traceback.format_exc())

    async def list_containers(self) -> dict:
        """
        List all containers in the cluster. Distinguishes between active (user) containers and warm containers.
        """
        logger.info("Listing all containers in the cluster...")
        if self.is_local:
            logger.info("Local mode: returning local container data only.")
            return {"active_containers": [], "warm_containers": []}

        try:
            response: dict = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )

            containers: list[dict] = []
            if response["taskArns"]:
                task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                    cluster=self.cluster_name,
                    tasks=response["taskArns"],
                    include=["TAGS"],
                )

                for task in task_details["tasks"]:
                    if "sandbox-manager" in task["taskDefinitionArn"]:
                        continue

                    task_id: str = task["taskArn"].split("/")[-1]
                    status: str = task["lastStatus"]

                    container_ip: str | None = None
                    if status == "RUNNING":
                        try:
                            container_ip = await self.get_container_ip(task_id)
                        except Exception as e:
                            logger.warning(
                                f"Could not retrieve IP for task_id={task_id}: {e}"
                            )
                            continue
                    else:
                        logger.debug(
                            f"Task_id={task_id} is not RUNNING (status={status})"
                        )
                        continue

                    if not container_ip:
                        continue

                    is_warm: bool = any(
                        tag["key"] == "type" and tag["value"] == "warm"
                        for tag in task.get("tags", [])
                    )

                    user_id: str = next(
                        (
                            tag["value"]
                            for tag in task.get("tags", [])
                            if tag["key"] == "user_id"
                        ),
                        "",
                    )
                    session_id: str = next(
                        (
                            tag["value"]
                            for tag in task.get("tags", [])
                            if tag["key"] == "session_id"
                        ),
                        "",
                    )

                    preview_port: int | None = None
                    if user_id and session_id:
                        container_info: ContainerInfo | None = (
                            await self.get_container_info(user_id, session_id)
                        )
                        if container_info:
                            preview_port = container_info.preview_port

                    created_at: float = task.get("createdAt", 0)
                    if hasattr(created_at, "timestamp"):
                        created_at = created_at.timestamp()
                    elif isinstance(created_at, (int, float)):
                        created_at = float(created_at)
                    else:
                        created_at = time.time()

                    containers.append(
                        {
                            "user_id": user_id,
                            "session_id": session_id,
                            "task_id": task_id,
                            "container_ip": container_ip,
                            "container_port": CONTAINER_PORT,
                            "preview_port": preview_port,
                            "status": status,
                            "created_at": created_at,
                            "is_warm": is_warm,
                        }
                    )

            containers.sort(key=lambda x: x["created_at"], reverse=True)
            active_containers: list[dict] = [c for c in containers if not c["is_warm"]]
            warm_containers: list[dict] = [c for c in containers if c["is_warm"]]

            logger.info(
                f"list_containers => active={len(active_containers)}, warm={len(warm_containers)}"
            )
            return {
                "active_containers": active_containers,
                "warm_containers": warm_containers,
            }

        except Exception as e:
            logger.error(f"Error listing containers from ECS: {e}")
            return {"active_containers": [], "warm_containers": []}

    async def kill_container(self, user_id: str, session_id: str):
        """
        Kill a specific container by user and session ID.
        If we have fewer than two arm container after, we will i) check
        if container is healthy. If healthy, convert to warm if no warm container is available.
        Otherwise, we stop it.
        """
        container_key: tuple[str, str] = (user_id, session_id)
        logger.info(f"Requested kill for container {container_key}")

        if self.is_local:
            logger.info("Local mode => removing from local registry only.")
            container_cache.remove(user_id, session_id)
            return True

        response: dict = await self.ecs.list_tasks(
            cluster=self.cluster_name, desiredStatus="RUNNING"
        )

        found_container: bool = False
        if response.get("taskArns"):
            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name, tasks=response["taskArns"], include=["TAGS"]
            )
            tasks: list[dict] = task_details["tasks"]

            for task in tasks:
                task_user: str | None = self.get_tag_value(
                    task.get("tags", []), "user_id"
                )
                task_session: str | None = self.get_tag_value(
                    task.get("tags", []), "session_id"
                )

                if task_user == user_id and task_session == session_id:
                    found_container: bool = True
                    task_id: str = self.extract_task_id(task["taskArn"])
                    logger.info(
                        f"Found task {task_id} for user_id={user_id}, session_id={session_id}"
                    )
                    try:
                        container_ip: str | None = await self.get_container_ip(task_id)
                        is_healthy, _ = await self.check_container_health_with_ip(
                            task_id, container_ip
                        )

                        warm_tasks: list[dict] = await self.list_warm_tasks()
                        healthy_warm_count: int = 0

                        for warm_task in warm_tasks:
                            wtask_id: str = self.extract_task_id(warm_task["taskArn"])
                            warm_ip: str = await self.get_container_ip(wtask_id)
                            (
                                warm_task_healthy,
                                _,
                            ) = await self.check_container_health_with_ip(
                                wtask_id, warm_ip
                            )
                            if warm_task_healthy:
                                healthy_warm_count += 1

                        if not is_healthy:
                            logger.info(
                                f"Container task_id={task_id} is unhealthy => cleaning up"
                            )
                            await self.cleanup_container(task_id)
                        elif healthy_warm_count >= MIN_WARM_CONTAINERS:
                            logger.info(
                                f"{healthy_warm_count} warm containers available => cleaning up {task_id}"
                            )
                            await self.cleanup_container(task_id)
                        else:
                            logger.info(
                                f"Not enough healthy warm containers => converting {task_id} to warm"
                            )
                            await self.update_task_tags(
                                task_id,
                                [
                                    {"key": "type", "value": "warm"},
                                    {"key": "user_id", "value": ""},
                                    {"key": "session_id", "value": ""},
                                ],
                            )
                        container_cache.remove(user_id, session_id)
                    except Exception as e:
                        logger.error(
                            f"Error while managing container {task_id} for user_id={user_id}, session_id={session_id}: {e}"
                        )
                        await self.cleanup_container(task_id)
                        container_cache.remove(user_id, session_id)

        return found_container

    async def start_container(self, user_id: str, session_id: str) -> ContainerInfo:
        """
        Start a new container for the user, reusing the warm container if possible.
        """
        logger.info(
            f"Starting container for user_id={user_id}, session_id={session_id}"
        )

        existing_container: ContainerInfo | None = await self.get_container_info(
            user_id, session_id
        )
        if existing_container and existing_container.status == "RUNNING":
            logger.info(f"Container for {user_id}/{session_id} is already RUNNING")
            return existing_container
        elif existing_container:
            logger.info("Container exists but not running, killing it first")
            await self.kill_container(user_id, session_id)
        if self.is_local:
            container_info: ContainerInfo = ContainerInfo(
                user_id=user_id,
                session_id=session_id,
                task_id=f"local-{user_id}-{session_id}",
                container_ip="localhost",
                container_port=CONTAINER_PORT,
                status="RUNNING",
                created_at=time.time(),
                is_warm=False,
            )
            container_cache.update(container_info)
            return container_info

        warm_tasks: list[dict] = await self.list_warm_tasks()
        logger.info(f"Trying to reuse one of {len(warm_tasks)} warm containers...")
        for warm_task in warm_tasks:
            task_id: str = warm_task["taskArn"].split("/")[-1]
            logger.debug(f"Attempting to reuse warm task_id={task_id}")
            try:
                task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                    cluster=self.cluster_name, tasks=[task_id]
                )
                tasks: list[dict] = task_details["tasks"]
                if not tasks:
                    logger.warning(f"Warm task {task_id} vanished from ECS, skipping")
                    continue

                task_status: str = tasks[0]["lastStatus"]
                if task_status != "RUNNING":
                    logger.warning(
                        f"Warm task {task_id} not in RUNNING state, status={task_status}"
                    )
                    continue

                try:
                    container_ip: str = await self.get_container_ip(task_id)
                except Exception as e:
                    logger.error(f"Could not retrieve IP for warm task {task_id}: {e}")
                    continue

                try:
                    is_healthy, _ = await self.check_container_health(
                        task_id, container_ip
                    )
                    if not is_healthy:
                        logger.warning(
                            f"Warm task {task_id} is not healthy, cleaning up"
                        )
                        await self.cleanup_container(task_id)
                        continue
                except Exception as e:
                    logger.error(f"Health check failed for warm task {task_id}: {e}")
                    continue

                await self.update_task_tags(
                    task_id,
                    [
                        {"key": "type", "value": "assigned"},
                        {"key": "user_id", "value": user_id},
                        {"key": "session_id", "value": session_id},
                    ],
                )

                try:
                    container_url = f"http://{container_ip}:{CONTAINER_PORT}"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{container_url}/run_command",
                            json={
                                "command": f"export SESSION_ID={session_id} && echo $SESSION_ID > /tmp/session_id",
                                "mode": "wait",
                                "path": "/",
                            },
                        ) as resp:
                            if resp.status == 200:
                                logger.info(
                                    f"Set SESSION_ID in container task_id={task_id}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to set SESSION_ID in container: {await resp.text()}"
                                )
                except Exception as e:
                    logger.warning(f"Error setting SESSION_ID in container: {e}")

                container_info = ContainerInfo(
                    user_id=user_id,
                    session_id=session_id,
                    task_id=task_id,
                    container_ip=container_ip,
                    container_port=CONTAINER_PORT,
                    status="RUNNING",
                    created_at=time.time(),
                    is_warm=False,
                )
                logger.info(
                    f"Reused warm container for {user_id}/{session_id} => task_id={task_id}"
                )
                container_cache.update(container_info)
                return container_info

            except Exception as e:
                logger.error(f"Error reusing warm container {task_id}: {e}")
                logger.info(f"Cleaning up warm container {task_id} due to error.")
                await self.cleanup_container(task_id)

        logger.info(
            "No warm container available or reuse failed; starting a new container."
        )

        task_params: dict = {
            "cluster": self.cluster_name,
            "taskDefinition": self.task_definition,
            "capacityProviderStrategy": [{"capacityProvider": "FARGATE", "weight": 1}],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": self.subnet_ids,
                    "securityGroups": [self.security_group_id],
                    "assignPublicIp": "ENABLED",
                }
            },
            "tags": [
                {"key": "type", "value": "assigned"},
                {"key": "user_id", "value": user_id},
                {"key": "session_id", "value": session_id},
            ],
            "overrides": {
                "containerOverrides": [
                    {
                        "name": "sandbox-container",
                        "environment": [
                            {"name": "SESSION_ID", "value": session_id},
                            {"name": "USER_ID", "value": user_id},
                        ],
                    }
                ]
            },
        }

        response: dict = await self.ecs.run_task(**task_params)

        task: dict = response["tasks"][0]
        task_id: str = task["taskArn"].split("/")[-1]
        logger.info(
            f"Launched new ECS task for {user_id}/{session_id}, task_id={task_id}"
        )

        await self.wait_for_container_ready(task_id)
        container_ip: str = await self.get_container_ip(task_id)
        container_info: ContainerInfo = ContainerInfo(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            container_ip=container_ip,
            container_port=CONTAINER_PORT,
            status="RUNNING",
            created_at=time.time(),
            is_warm=False,
        )
        logger.info(
            f"Container {task_id} is running and ready for {user_id}/{session_id}"
        )
        container_cache.update(container_info)
        return container_info

    async def get_container_ip(self, task_id: str) -> str:
        """
        Retrieve the public IP for a container given its ECS task_id.
        """
        logger.debug(f"Retrieving container IP for task_id={task_id}")

        task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
            cluster=self.cluster_name, tasks=[task_id]
        )
        tasks: list[dict] = task_details["tasks"]
        if tasks:
            task: dict = tasks[0]
            for attachment in task.get("attachments", []):
                if attachment["type"] == "ElasticNetworkInterface":
                    eni_id: str = next(
                        (
                            d["value"]
                            for d in attachment["details"]
                            if d["name"] == "networkInterfaceId"
                        ),
                        None,
                    )
                    if eni_id:
                        eni_response = await self.ec2.describe_network_interfaces(
                            NetworkInterfaceIds=[eni_id]
                        )
                        nic = eni_response["NetworkInterfaces"][0]
                        if "Association" in nic and "PublicIp" in nic["Association"]:
                            return nic["Association"]["PublicIp"]
        raise ConnectionRefusedError(
            f"Unable to determine IP for task_id={task_id}, maybe it's not ready."
        )

    async def wait_for_container_ready(self, task_id: str, max_retries: int = 200):
        """
        Wait for a container to transition into RUNNING and pass the /health check.
        """
        logger.info(
            f"Waiting for container task_id={task_id} to be ready, up to {max_retries} checks."
        )
        if self.is_local:
            logger.info("Local mode => returning immediately.")
            return

        for attempt in range(max_retries):
            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name, tasks=[task_id]
            )
            tasks: list[dict] = task_details["tasks"]
            if not tasks:
                logger.error(f"Task {task_id} not found in cluster; giving up.")
                raise ConnectionRefusedError("ECS Task not found in cluster")

            task: dict = tasks[0]
            status: str = task["lastStatus"]
            logger.debug(f"Task {task_id} status check => {status} (attempt={attempt})")

            if status == "PENDING":
                logger.debug(f"Task {task_id} is pending (attempt={attempt}).")
            elif status == "RUNNING":
                try:
                    container_ip = await self.get_container_ip(task_id)
                    is_healthy, _ = await self.check_container_health(
                        task_id, container_ip, startup_grace_period=True
                    )
                    if is_healthy:
                        logger.info(f"Task {task_id} is RUNNING and healthy.")
                        return
                    else:
                        logger.debug(
                            f"Task {task_id} is RUNNING but not healthy yet (attempt={attempt})"
                        )
                except Exception as e:
                    logger.warning(
                        f"Container {task_id} RUNNING but health check failed: {e}"
                    )
            elif status == "STOPPED":
                stopped_reason = task.get("stoppedReason", "Unknown reason")
                logger.error(f"Task {task_id} STOPPED, reason={stopped_reason}")
                if (
                    "containers" in task
                    and task["containers"]
                    and "reason" in task["containers"][0]
                ):
                    logger.error(f"Container reason: {task['containers'][0]['reason']}")
                raise ConnectionAbortedError(
                    f"Task {task_id} stopped. Reason={stopped_reason}"
                )
            await asyncio.sleep(1)

        logger.error(
            f"Task {task_id} not ready after {max_retries} attempts, giving up."
        )
        raise ConnectionRefusedError(
            f"Container {task_id} failed to start within allowed retries (status={status})."
        )

    async def list_warm_tasks(self) -> list[dict]:
        """
        Return all ECS tasks that are labeled as warm, are running, and do not have user/session tags.
        """
        logger.debug("Listing warm tasks from ECS.")
        if self.is_local:
            logger.debug("Local mode => returning empty warm task list.")
            return []

        try:
            response: dict = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )
            if not response["taskArns"]:
                logger.debug("No running tasks => no warm tasks found.")
                return []

            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name,
                tasks=response["taskArns"],
                include=["TAGS"],
            )

            warm_tasks: list[dict] = []
            for task in task_details["tasks"]:
                if "sandbox-manager" in task["taskDefinitionArn"]:
                    continue

                if (
                    task["lastStatus"] != "RUNNING"
                    or task.get("desiredStatus") != "RUNNING"
                ):
                    continue

                task_tags: list[dict] = task.get("tags", [])
                is_warm_tagged: bool = False
                has_user_id: bool = False

                for tag in task_tags:
                    if tag.get("key") == "type" and tag.get("value") == "warm":
                        is_warm_tagged = True
                    if tag.get("key") == "user_id" and tag.get("value"):
                        has_user_id = True

                if not has_user_id and is_warm_tagged:
                    warm_tasks.append(task)

            logger.info(
                f"{len(warm_tasks)} warm tasks found. Task IDs: {[task['taskArn'].split('/')[-1] for task in warm_tasks]}"
            )
            return warm_tasks

        except Exception as e:
            logger.error(f"Error fetching warm tasks: {e}")
            return []

    async def update_task_tags(self, task_id: str, tags: list[dict]):
        """
        Merge updated tags into existing tags for the given ECS task.
        """
        logger.debug(f"Updating tags for task_id={task_id}, tags={tags}")
        if self.is_local:
            logger.debug("Local mode => skipping AWS tag updates.")
            return

        try:
            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name, tasks=[task_id]
            )
            tasks: list[dict] = task_details["tasks"]
            if not tasks:
                logger.error(f"Task {task_id} not found while updating tags.")
                return

            task: dict = tasks[0]
            task_arn: str = task["taskArn"]
            existing_tags: list[dict] = task.get("tags", [])
            tag_map: dict[str, str] = {t["key"]: t["value"] for t in existing_tags}

            for tag_item in tags:
                tag_map[tag_item["key"]] = tag_item["value"]

            merged_tags = [{"key": k, "value": v} for k, v in tag_map.items()]
            await self.ecs.tag_resource(resourceArn=task_arn, tags=merged_tags)
            logger.info(f"Updated tags for task_id={task_id} => {merged_tags}")
        except Exception as e:
            logger.error(f"Error updating task {task_id} tags: {e}")

    async def get_container_info(
        self, user_id: str, session_id: str
    ) -> ContainerInfo | None:
        """
        Retrieve ContainerInfo for specified user_id/session_id by searching ECS tasks.
        """
        if self.is_local:
            return None

        try:
            response: dict = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )

            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name,
                tasks=response["taskArns"],
                include=["TAGS"],
            )
            tasks: list[dict] = task_details["tasks"]

            for task in tasks:
                task_user: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "user_id"
                    ),
                    None,
                )
                task_session: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "session_id"
                    ),
                    None,
                )

                if task_user == user_id and task_session == session_id:
                    task_id: str = task["taskArn"].split("/")[-1]
                    container_ip: str = await self.get_container_ip(task_id)

                    preview_port: int | None = next(
                        (
                            int(tag["value"])
                            for tag in task.get("tags", [])
                            if tag["key"] == "preview_port"
                        ),
                        None,
                    )

                    container_info = ContainerInfo(
                        user_id=user_id,
                        session_id=session_id,
                        task_id=task_id,
                        container_ip=container_ip,
                        container_port=CONTAINER_PORT,
                        status=task["lastStatus"],
                        created_at=(
                            task.get("createdAt", time.time()).timestamp()
                            if hasattr(task.get("createdAt"), "timestamp")
                            else time.time()
                        ),
                        is_warm=False,
                        preview_port=preview_port,
                    )

                    container_cache.update(container_info)

                    return container_info

            return None

        except Exception as e:
            logger.error(f"Error getting container info: {e}")
            logger.error(traceback.format_exc())
            return None

    async def set_preview_port(self, user_id: str, session_id: str, port: int) -> bool:
        """
        Set the preview port for a given user's container by updating its tags.
        """
        if self.is_local:
            return False

        try:
            response: dict = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )
            if not response["taskArns"]:
                return False

            task_details: dict = await self.ecs.describe_tasks(
                cluster=self.cluster_name,
                tasks=response["taskArns"],
                include=["TAGS"],
            )
            tasks: list[dict] = task_details["tasks"]

            for task in tasks:
                task_user: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "user_id"
                    ),
                    None,
                )
                task_session: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "session_id"
                    ),
                    None,
                )

                if task_user == user_id and task_session == session_id:
                    task_id: str = task["taskArn"].split("/")[-1]
                    await self.update_task_tags(
                        task_id, [{"key": "preview_port", "value": str(port)}]
                    )
                    container_info: ContainerInfo | None = (
                        await self.get_container_info(user_id, session_id)
                    )
                    if container_info:
                        container_info.preview_port = port
                        container_cache.update(container_info)

                    return True

            return False

        except Exception as e:
            logger.error(f"Error setting preview port: {e}")
            logger.error(traceback.format_exc())
            return False

    async def get_user_sandboxes(self, user_id: str) -> dict[str, ContainerInfo]:
        """
        Returns a dict of session_id => ContainerInfo for all sessions belonging to user_id.
        """
        if self.is_local:
            return {}

        try:
            result: dict[str, ContainerInfo] = {}
            response: dict = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )
            if not response["taskArns"]:
                return result

            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name,
                tasks=response["taskArns"],
                include=["TAGS"],
            )
            tasks: list[dict] = task_details["tasks"]

            for task in tasks:
                task_user: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "user_id"
                    ),
                    None,
                )
                task_session: str | None = next(
                    (
                        tag["value"]
                        for tag in task.get("tags", [])
                        if tag["key"] == "session_id"
                    ),
                    None,
                )

                if task_user == user_id and task_session:
                    task_id: str = task["taskArn"].split("/")[-1]
                    preview_port: int | None = next(
                        (
                            int(tag["value"])
                            for tag in task.get("tags", [])
                            if tag["key"] == "preview_port"
                        ),
                        None,
                    )

                    result[task_session] = ContainerInfo(
                        user_id=task_user,
                        session_id=task_session,
                        task_id=task_id,
                        container_ip=None,
                        container_port=CONTAINER_PORT,
                        status=task["lastStatus"],
                        created_at=(
                            task.get("createdAt", time.time()).timestamp()
                            if hasattr(task.get("createdAt"), "timestamp")
                            else time.time()
                        ),
                        is_warm=False,
                        preview_port=preview_port,
                    )

            return result

        except Exception as e:
            logger.error(f"Error getting user sandboxes: {e}")
            return {}

    def configure_networking(
        self, subnet_ids: list[str], security_group_id: str, efs_filesystem_id: str = ""
    ):
        """
        Configure networking details (subnets, security groups) from Terraform outputs or environment.
        """
        self.subnet_ids = subnet_ids
        self.security_group_id = security_group_id
        if efs_filesystem_id:
            self.efs_filesystem_id = efs_filesystem_id
            logger.info(f"Configured EFS filesystem ID: {self.efs_filesystem_id}")

    def extract_task_id(self, task_arn: str) -> str:
        """Extract task ID from ARN."""
        return task_arn.split("/")[-1]

    def get_tag_value(self, tags: list[dict], key: str) -> str | None:
        """Get value for a specific tag key."""
        return next((tag["value"] for tag in tags if tag["key"] == key), None)

    async def check_container_health_with_ip(
        self, task_id: str, container_ip: str, startup_grace_period: bool = False
    ) -> tuple[bool, float | None]:
        """Helper method to check container health when IP is already known."""
        is_healthy, last_disconnect = await self.check_container_health(
            task_id, container_ip, startup_grace_period
        )
        return is_healthy, last_disconnect

    async def _get_public_ip_for_task(self, task_id: str, private_ip: str) -> list[str]:
        """Helper to get public IP for a task if available."""
        ips_to_try: list[str] = []

        if not private_ip.startswith(AWS_PRIVATE_IP_PREFIX):
            return [private_ip]

        try:
            task_details: dict[str, list[dict]] = await self.ecs.describe_tasks(
                cluster=self.cluster_name, tasks=[task_id]
            )
            tasks: list[dict] = task_details["tasks"]
            if not tasks:
                return [private_ip]

            eni_id: str | None = None
            for attachment in tasks[0].get("attachments", []):
                if attachment["type"] == AWS_ENI_TYPE:
                    for detail in attachment["details"]:
                        if detail["name"] == AWS_ENI_ID_KEY:
                            eni_id = detail["value"]
                            break

            if eni_id:
                eni_response: dict = await self.ec2.describe_network_interfaces(
                    NetworkInterfaceIds=[eni_id]
                )
                if (
                    eni_response["NetworkInterfaces"]
                    and "Association" in eni_response["NetworkInterfaces"][0]
                ):
                    public_ip: str | None = eni_response["NetworkInterfaces"][0][
                        "Association"
                    ].get("PublicIp")
                    if public_ip:
                        logger.debug(
                            f"Found public IP {public_ip} for task_id={task_id}"
                        )
                        ips_to_try.append(public_ip)

        except Exception as e:
            logger.debug(f"Could not retrieve public IP for task_id={task_id}: {e}")

        ips_to_try.append(private_ip)
        return ips_to_try

    async def list_dir_caches(self) -> list[dict]:
        """
        List all directory caches.
        This operation accesses EFS directly.
        """
        try:
            dir_cache_path: str = "/efs/dir-cache"
            metadata_file: str = os.path.join(dir_cache_path, "cache_metadata.json")

            if not os.path.exists(dir_cache_path):
                logger.warning(f"Directory cache path {dir_cache_path} does not exist")
                return []

            metadata: dict = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error reading cache metadata: {e}")

            caches: list[dict] = []
            for cache_name, cache_info in metadata.items():
                cache_path: str = os.path.join(dir_cache_path, cache_name)
                if not os.path.exists(cache_path):
                    continue

                caches.append(
                    {
                        "name": cache_name,
                        "size_mb": cache_info.get("size_mb", 0),
                        "created": cache_info.get("created", ""),
                        "last_restored": cache_info.get("last_restored", ""),
                    }
                )

            caches.sort(
                key=lambda x: x.get("last_restored", x.get("created", "")), reverse=True
            )

            return caches

        except Exception as e:
            logger.error(f"Error listing directory caches: {e}")
            return []

    async def delete_dir_cache(self, cache_name: str) -> bool:
        """
        Delete a directory cache from EFS.
        This operation accesses EFS directly.
        """
        try:
            dir_cache_path: str = "/efs/dir-cache"
            metadata_file: str = os.path.join(dir_cache_path, "cache_metadata.json")
            cache_path: str = os.path.join(dir_cache_path, cache_name)

            if not os.path.exists(cache_path):
                logger.warning(f"Cache file {cache_name} not found")
                return False

            os.remove(cache_path)

            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, "r") as f:
                        metadata: dict = json.load(f)

                    if cache_name in metadata:
                        del metadata[cache_name]

                    with open(metadata_file, "w") as f:
                        json.dump(metadata, f)
                except Exception as e:
                    logger.error(f"Error updating cache metadata: {e}")

            return True

        except Exception as e:
            logger.error(f"Error deleting directory cache {cache_name}: {e}")
            return False

    async def cleanup_excess_warm_containers(self, max_keep: int = 2) -> None:
        """
        Emergency cleanup function that directly uses ECS API to clean up excess warm containers.
        This is a fallback for when normal tag-based detection isn't working.
        """
        logger.info(
            f"Emergency cleanup: Ensuring no more than {max_keep} warm containers"
        )

        if self.is_local:
            logger.info("Local mode => skipping emergency cleanup")
            return

        try:
            response = await self.ecs.list_tasks(
                cluster=self.cluster_name, desiredStatus="RUNNING"
            )

            if not response["taskArns"]:
                logger.info("No running tasks found in ECS")
                return

            task_details = await self.ecs.describe_tasks(
                cluster=self.cluster_name,
                tasks=response["taskArns"],
                include=["TAGS"],
            )
            warm_candidates: list[dict] = []

            for task in task_details["tasks"]:
                if "sandbox-manager" in task["taskDefinitionArn"]:
                    continue

                if task["lastStatus"] != "RUNNING":
                    continue

                task_id: str = task["taskArn"].split("/")[-1]
                task_tags: list[dict] = task.get("tags", [])

                is_warm_tagged: bool = False
                has_user_id: bool = False

                for tag in task_tags:
                    if tag.get("key") == "type" and tag.get("value") == "warm":
                        is_warm_tagged = True
                    if tag.get("key") == "user_id" and tag.get("value"):
                        has_user_id = True

                if is_warm_tagged or not has_user_id:
                    task["_is_warm_tagged"] = is_warm_tagged
                    task["_has_user_id"] = has_user_id
                    warm_candidates.append(task)

            warm_candidates.sort(
                key=lambda t: (
                    not t.get("_is_warm_tagged", False),
                    -1
                    * (
                        t.get("startedAt", 0)
                        if hasattr(t.get("startedAt"), "timestamp")
                        else (
                            time.time()
                            if t.get("startedAt") is None
                            else t.get("startedAt")
                        )
                    ),
                )
            )

            if len(warm_candidates) > max_keep:
                to_cleanup = warm_candidates[max_keep:]
                logger.info(
                    f"Found {len(warm_candidates)} potential warm containers, keeping {max_keep}, "
                    f"cleaning up {len(to_cleanup)}"
                )

                for task in to_cleanup:
                    task_id = task["taskArn"].split("/")[-1]
                    logger.info(f"Emergency cleanup: stopping task {task_id}")
                    await self.cleanup_container(task_id)
                    await asyncio.sleep(0.5)

            else:
                logger.info(
                    f"Found {len(warm_candidates)} potential warm containers, "
                    f"which is <= {max_keep}, no cleanup needed"
                )

        except Exception as e:
            logger.error(f"Error in emergency cleanup: {e}")
            logger.error(traceback.format_exc())


container_manager: ContainerManager = ContainerManager(
    cluster_name="sandbox-cluster",
    task_definition="sandbox-container",
    subnet_ids=[],
    security_group_id="",
    efs_filesystem_id="",
    is_local=False,
)
