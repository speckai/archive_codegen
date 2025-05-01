import time

from loguru import logger
from src.schemas import ContainerInfo


class ContainerCache:
    def __init__(self, ttl_seconds: int = 60):
        self._cache: dict[tuple[str, str], tuple[ContainerInfo, float]] = {}
        self.ttl_seconds: int = ttl_seconds
        logger.info(f"Initialized ContainerCache with TTL={ttl_seconds}s")

    def get(self, user_id: str, session_id: str) -> ContainerInfo | None:
        key: tuple[str, str] = (user_id, session_id)
        if key in self._cache:
            container_info, timestamp = self._cache[key]

            if time.time() - timestamp <= self.ttl_seconds:
                logger.debug(f"Cache hit for {user_id}/{session_id}")
                return container_info
            else:
                logger.debug(f"Cache expired for {user_id}/{session_id}")
                del self._cache[key]

        logger.debug(f"Cache miss for {user_id}/{session_id}")
        return None

    def update(self, container_info: ContainerInfo) -> None:
        if (
            not container_info
            or not container_info.user_id
            or not container_info.session_id
        ):
            logger.warning("Attempted to cache invalid container info")
            return

        key: tuple[str, str] = (container_info.user_id, container_info.session_id)
        self._cache[key] = (container_info, time.time())
        logger.debug(
            f"Updated cache for {container_info.user_id}/{container_info.session_id}"
        )

    def remove(self, user_id: str, session_id: str) -> None:
        key: tuple[str, str] = (user_id, session_id)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Removed {user_id}/{session_id} from cache")

    def clear(self) -> None:
        self._cache.clear()
        logger.info("Container cache cleared")

    def cleanup_expired(self) -> int:
        now: float = time.time()
        expired_keys: list[tuple[str, str]] = [
            key
            for key, (_, timestamp) in self._cache.items()
            if now - timestamp > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


container_cache: ContainerCache = ContainerCache()
