import asyncio
import contextlib
import random
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from src.manager.container_manager import ContainerManager

# Watchdog-specific constants
CLEANUP_INTERVAL_SECONDS: int = 5  # Run cleanup loop frequently
INACTIVITY_TIMEOUT_SECONDS: int = 30  # Seconds of inactivity before cleanup
MIN_WARM_CONTAINERS: int = 2  # Warm containers
STARTUP_GRACE_PERIOD_SECONDS: int = 30  # Initial container startup time
WARMUP_LOOP_INTERVAL_SECONDS: int = 15  # Base interval for warmup checks
WARMUP_JITTER_SECONDS: int = 2  # Random jitter range for warmup


class ManagerWatchdog:
    def __init__(self, container_manager: "ContainerManager"):
        self.container_manager: "ContainerManager" = container_manager
        self._cleanup_task: asyncio.Task | None = None
        self._warmup_task: asyncio.Task | None = None
        self._warmup_lock: asyncio.Lock = asyncio.Lock()

    async def start(self):
        """Start the watchdog tasks."""
        await self.start_cleanup_task()
        await self.start_warmup_task()

    async def stop(self):
        """Stop the watchdog tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

        if self._warmup_task:
            self._warmup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._warmup_task
            self._warmup_task = None

    async def start_cleanup_task(self):
        """Ensure the cleanup loop is running in background."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def start_warmup_task(self):
        """Ensure the warmup loop is running in background."""
        if self._warmup_task is None or self._warmup_task.done():
            self._warmup_task = asyncio.create_task(self._warmup_loop())

    async def _ensure_warm_pool(self):
        if self.container_manager.is_local:
            logger.debug("Local mode: skipping warm pool management.")
            return

        async with self._warmup_lock:
            logger.info("Ensuring at least two warm containers in the pool.")
            try:
                warm_tasks: list[dict[str, Any]] = (
                    await self.container_manager.list_warm_tasks()
                )
                logger.info(
                    f"Found {len(warm_tasks)} warm tasks in _ensure_warm_pool()"
                )

                healthy_warm_count: int = 0
                for task in warm_tasks:
                    task_id: str = self.container_manager.extract_task_id(
                        task["taskArn"]
                    )
                    logger.debug(f"Health checking warm task: {task_id}")
                    container_ip: str = await self.container_manager.get_container_ip(
                        task_id
                    )
                    (
                        is_healthy,
                        last_disconnect,
                    ) = await self.container_manager.check_container_health_with_ip(
                        task_id, container_ip
                    )
                    if is_healthy:
                        logger.info(f"Warm container {task_id} is healthy")
                        healthy_warm_count += 1
                    else:
                        logger.info(
                            f"Warm container {task_id} is unhealthy, cleaning up"
                        )
                        await self.container_manager.cleanup_container(task_id)

                if healthy_warm_count >= MIN_WARM_CONTAINERS:
                    logger.info(
                        f"({healthy_warm_count}) healthy warm containers found, no action needed."
                    )
                    return

                logger.info(
                    f"Need a warm container. Currently healthy warm count={healthy_warm_count}, required=2"
                )

                ecs_response: dict[str, list[str]] = (
                    await self.container_manager.ecs.list_tasks(
                        cluster=self.container_manager.cluster_name,
                        desiredStatus="RUNNING",
                    )
                )
                if ecs_response["taskArns"]:
                    tasks_response: dict[str, list[dict[str, Any]]] = (
                        await self.container_manager.ecs.describe_tasks(
                            cluster=self.container_manager.cluster_name,
                            tasks=ecs_response["taskArns"],
                            include=["TAGS"],
                        )
                    )
                    tasks: list[dict[str, Any]] = tasks_response["tasks"]

                    for task in tasks:
                        task_id: str = self.container_manager.extract_task_id(
                            task["taskArn"]
                        )
                        task_tags: list[dict[str, str]] = task.get("tags", [])

                        if any(
                            tag["key"] == "type" and tag["value"] == "warm"
                            for tag in task_tags
                        ):
                            logger.debug(f"Skipping task {task_id}, already warm.")
                            continue

                        has_user: bool = (
                            self.container_manager.get_tag_value(task_tags, "user_id")
                            is not None
                        )
                        has_session: bool = (
                            self.container_manager.get_tag_value(
                                task_tags, "session_id"
                            )
                            is not None
                        )

                        if not has_user and not has_session:
                            logger.info(
                                f"Converting unassigned running task {task_id} to warm"
                            )
                            container_ip: str = (
                                await self.container_manager.get_container_ip(task_id)
                            )
                            (
                                is_healthy,
                                last_disconnect,
                            ) = await self.container_manager.check_container_health_with_ip(
                                task_id, container_ip
                            )
                            if is_healthy:
                                logger.info(
                                    f"Task {task_id} is healthy, tagging as warm"
                                )
                                await self.container_manager.update_task_tags(
                                    task_id, [{"key": "type", "value": "warm"}]
                                )
                                return
                            else:
                                logger.info(
                                    f"Task {task_id} is unhealthy or not ready, cleaning up"
                                )
                                await self.container_manager.cleanup_container(task_id)

                logger.info("No convertible tasks found; starting new warm container.")
                try:
                    ecs_run_response: dict[str, Any] = (
                        await self.container_manager.ecs.run_task(
                            cluster=self.container_manager.cluster_name,
                            taskDefinition=self.container_manager.task_definition,
                            capacityProviderStrategy=[
                                {"capacityProvider": "FARGATE", "weight": 1}
                            ],
                            networkConfiguration={
                                "awsvpcConfiguration": {
                                    "subnets": self.container_manager.subnet_ids,
                                    "securityGroups": [
                                        self.container_manager.security_group_id
                                    ],
                                    "assignPublicIp": "ENABLED",
                                }
                            },
                            tags=[{"key": "type", "value": "warm"}],
                        )
                    )
                    if ecs_run_response["tasks"]:
                        task_id: str = ecs_run_response["tasks"][0]["taskArn"].split(
                            "/"
                        )[-1]
                        logger.info(f"Started new warm container {task_id}")
                        try:
                            await self.container_manager.wait_for_container_ready(
                                task_id, max_retries=60
                            )
                            logger.info(f"New warm container {task_id} is ready")
                        except Exception as e:
                            logger.error(
                                f"New warm container {task_id} failed to become ready: {e}"
                            )
                            await self.container_manager.cleanup_container(task_id)
                except Exception as e:
                    logger.error(f"Error starting warm container: {e}")

            except Exception as e:
                logger.error(f"Error ensuring warm pool: {e}")

    async def _cleanup_loop(self):
        """Periodically scans for containers that should be cleaned up."""
        if self.container_manager.is_local:
            logger.info("Cleanup loop is disabled in local mode.")
            return

        while True:
            try:
                response: dict = await self.container_manager.ecs.list_tasks(
                    cluster=self.container_manager.cluster_name,
                    desiredStatus="RUNNING",
                )
                if not response["taskArns"]:
                    logger.debug("No running tasks found. Sleeping.")
                    await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                    continue

                tasks: dict = await self.container_manager.ecs.describe_tasks(
                    cluster=self.container_manager.cluster_name,
                    tasks=response["taskArns"],
                    include=["TAGS"],
                )

                warm_tasks: list[dict] = await self.container_manager.list_warm_tasks()
                warm_count: int = len(warm_tasks)
                logger.debug(
                    f"Found {warm_count} warm tasks, ensuring we keep only {MIN_WARM_CONTAINERS}."
                )

                warm_tasks.sort(key=lambda t: t.get("startedAt", 0), reverse=True)
                if warm_count > MIN_WARM_CONTAINERS:
                    tasks_to_spare: int = warm_count - MIN_WARM_CONTAINERS
                    tasks_to_cleanup: list[dict] = warm_tasks[MIN_WARM_CONTAINERS:]
                    logger.info(
                        f"Excess warm containers: {tasks_to_spare}, will cleanup older tasks."
                    )
                    for task in tasks_to_cleanup:
                        task_id = self.container_manager.extract_task_id(
                            task["taskArn"]
                        )
                        logger.info(f"Cleaning up extra warm container {task_id}")
                        await self.container_manager.cleanup_container(task_id)

                for task in tasks["tasks"]:
                    task_id: str = self.container_manager.extract_task_id(
                        task["taskArn"]
                    )

                    if "sandbox-manager" in task["taskDefinitionArn"]:
                        continue

                    container_ip: str | None = None
                    try:
                        container_ip = await self.container_manager.get_container_ip(
                            task_id
                        )
                    except Exception as e:
                        logger.warning(
                            f"Skipping IP fetch for {task_id} in cleanup loop: {e}"
                        )

                    if not container_ip:
                        continue

                    (
                        is_healthy,
                        last_disconnect,
                    ) = await self.container_manager.check_container_health_with_ip(
                        task_id, container_ip
                    )
                    is_warm: bool = any(
                        tag["key"] == "type" and tag["value"] == "warm"
                        for tag in task.get("tags", [])
                    )

                    start_time: float = task.get("startedAt")
                    if hasattr(start_time, "timestamp"):
                        start_time = start_time.timestamp()
                    if not start_time:
                        start_time = time.time()

                    time_since_start: float = time.time() - start_time

                    has_user_tag: bool = (
                        self.container_manager.get_tag_value(
                            task.get("tags", []), "user_id"
                        )
                        is not None
                    )
                    has_session_tag: bool = (
                        self.container_manager.get_tag_value(
                            task.get("tags", []), "session_id"
                        )
                        is not None
                    )
                    is_orphaned: bool = not is_warm and not (
                        has_user_tag and has_session_tag
                    )

                    should_cleanup: bool = False
                    if is_orphaned:
                        logger.info(
                            f"Task {task_id} is orphaned => scheduling cleanup."
                        )
                        should_cleanup = True
                    elif (
                        not is_healthy
                        and time_since_start > STARTUP_GRACE_PERIOD_SECONDS
                        and (not is_warm or warm_count > MIN_WARM_CONTAINERS)
                    ):
                        logger.info(
                            f"Task {task_id} is unhealthy after grace => scheduling cleanup."
                        )
                        should_cleanup = True
                    elif (
                        last_disconnect
                        and (time.time() - last_disconnect > INACTIVITY_TIMEOUT_SECONDS)
                        and (
                            not is_warm
                            or not is_healthy
                            or warm_count > MIN_WARM_CONTAINERS
                        )
                    ):
                        logger.info(
                            f"Task {task_id} is inactive => scheduling cleanup."
                        )
                        should_cleanup = True

                    if should_cleanup:
                        await self.container_manager.cleanup_container(task_id)

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    async def _warmup_loop(self):
        """Periodically ensures at least one container is warm."""
        if self.container_manager.is_local:
            logger.info("Warmup loop ignored in local mode.")
            return

        logger.info("Starting warmup loop for ContainerManager")
        while True:
            try:
                logger.debug("Warmup loop iteration: ensuring warm pool")
                await self._ensure_warm_pool()
            except Exception as e:
                logger.error(f"Error in warmup loop: {e}")

            # For herd scenarios
            jitter: float = random.uniform(0, WARMUP_JITTER_SECONDS)
            await asyncio.sleep(WARMUP_LOOP_INTERVAL_SECONDS + jitter)
