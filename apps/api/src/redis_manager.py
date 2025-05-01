import os
import uuid

import redis.asyncio as redis
from src.config import DEV, IS_DOCKER
from src.utils.logging import logger


class _RedisManager:
    def __init__(self):
        self.redis_url: str = (
            "redis://host.docker.internal:6379"
            if (DEV and IS_DOCKER)
            else (
                "redis://localhost:6379"
                if DEV
                else os.getenv("REDIS_CONNECTION_STRING")
            )
        )
        self.redis_client: redis.Redis | None = None
        self.worker_id: str = os.getenv("WORKER_ID", "dev-worker")

    ### Task stuff
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            if not self.redis_client:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info(f"Connected to Redis with worker ID: {self.worker_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def get_worker_for_user(self, user_id: str) -> str | None:
        """Get the worker ID handling a user's task"""
        try:
            if not self.redis_client:
                await self.connect()
            worker: bytes | None = await self.redis_client.get(f"worker:user:{user_id}")
            return None if worker is None else worker.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to get worker for user {user_id}: {str(e)}")
            return None

    async def set_worker_for_user(self, user_id: str) -> None:
        """Assign the current worker to handle a user's task"""
        try:
            if not self.redis_client:
                await self.connect()
            await self.redis_client.set(f"worker:user:{user_id}", self.worker_id)
        except Exception as e:
            logger.error(f"Failed to set worker for user {user_id}: {str(e)}")
            raise

    async def remove_worker_for_user(self, user_id: str) -> None:
        """Remove the worker assignment for a user"""
        try:
            if not self.redis_client:
                await self.connect()
            await self.redis_client.delete(f"worker:user:{user_id}")
        except Exception as e:
            logger.error(f"Failed to remove worker for user {user_id}: {str(e)}")

    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    ### GitHub stuff
    async def set_comment_has_been_answered(
        self, issue_id: int, comment_id: int
    ) -> None:
        """Set a comment as having been answered"""
        try:
            if not self.redis_client:
                await self.connect()
            await self.redis_client.set(
                f"comment:answered:{issue_id}:{comment_id}", "true"
            )
        except Exception as e:
            logger.error(f"Failed to set comment {comment_id} as answered: {str(e)}")
            raise

    async def get_comment_has_been_answered(
        self, issue_id: int, comment_id: int
    ) -> bool:
        """Get a comment as having been answered"""
        try:
            if not self.redis_client:
                await self.connect()
            return await self.redis_client.get(
                f"comment:answered:{issue_id}:{comment_id}"
            )
        except Exception as e:
            logger.error(f"Failed to get comment {comment_id} as answered: {str(e)}")
            return False

    async def request_task_id(
        self, git_repo_id: str, workspace_name: str, issue_number: str | None = None
    ) -> str:
        """Get a task ID and mark the task ID with the given git repo ID and space name"""
        try:
            if not self.redis_client:
                await self.connect()

            task_id: str = str(uuid.uuid4())

            tr: redis.Redis = self.redis_client.pipeline()
            tr.set(f"task:git_repo_id:{task_id}", git_repo_id)
            tr.set(f"task:workspace_name:{task_id}", workspace_name)
            if issue_number:
                tr.set(f"task:issue_number:{task_id}", issue_number)
            await tr.execute()

            return task_id
        except Exception as e:
            logger.error(f"Failed to request task ID: {str(e)}")
            raise

    async def retrieve_task_id(self, task_id: str) -> tuple[int, str, int | None]:
        """Retrieve the git repo ID and space name for a task ID and delete the task ID"""
        try:
            if not self.redis_client:
                await self.connect()

            tr: redis.Redis = self.redis_client.pipeline()
            tr.get(f"task:git_repo_id:{task_id}")
            tr.get(f"task:workspace_name:{task_id}")
            tr.get(f"task:issue_number:{task_id}")

            results = await tr.execute()
            git_repo_id, workspace_name_bytes, issue_number_bytes = (
                results[0],
                results[1],
                results[2],
            )

            workspace_name: str = workspace_name_bytes.decode("utf-8")
            if not git_repo_id or not workspace_name:
                return (-1, "", None)

            issue_number = int(issue_number_bytes) if issue_number_bytes else None
            return (int(git_repo_id), workspace_name, issue_number)
        except Exception as e:
            logger.error(f"Failed to retrieve task ID {task_id}: {str(e)}")
            return (-1, "", None)

    async def delete_task_id(self, task_id: str) -> bool:
        """Delete a task ID"""
        try:
            if not self.redis_client:
                await self.connect()

            tr: redis.Redis = self.redis_client.pipeline()
            tr.delete(f"task:git_repo_id:{task_id}")
            tr.delete(f"task:workspace_name:{task_id}")
            tr.delete(f"task:issue_number:{task_id}")
            results = await tr.execute()

            return any(result == 1 for result in results)
        except Exception as e:
            logger.error(f"Failed to delete task ID {task_id}: {str(e)}")
            return False


RedisManager = _RedisManager()
