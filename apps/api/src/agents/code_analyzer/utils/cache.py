"""
Cache implementations for the code analyzer module.
Provides flexible caching mechanisms with invalidation protocols.
"""

import time
from typing import Protocol


class BaseCache(Protocol):
    """Base protocol for all caches with invalidation support."""

    def invalidate(self) -> None:
        """
        Invalidate the cache, forcing a refresh on next use.

        :return: None
        """
        pass

    @property
    def is_valid(self) -> bool:
        """
        Check if the cache is currently valid.

        :return: True if cache is valid, False otherwise
        """
        pass


class CodebaseGraphCache(BaseCache):
    """
    Cache for import relationships between files.
    Stores import and importer relationships for BFS traversal.
    Cache is invalidated when files are modified rather than using TTL.
    """

    def __init__(self):
        """
        Initialize the BFS cache.
        """
        self.cache: dict[str, dict[str, list[str]]] = {}
        self._timestamp: float = 0
        self._is_valid: bool = False

    def invalidate(self) -> None:
        """
        Invalidate the cache when repository changes.

        :return: None
        """
        self._is_valid = False
        self.cache = {}

    @property
    def is_valid(self) -> bool:
        """
        Check if the cache is valid.

        :return: True if cache is valid, False otherwise
        """
        return self._is_valid and bool(self.cache)

    def set_cache(self, cache_data: dict[str, dict[str, list[str]]]) -> None:
        """
        Set the cache data and mark as valid.

        :param cache_data: The import relationship data to cache
        :return: None
        """
        self.cache = cache_data
        self._timestamp = time.time()
        self._is_valid = True

    def get_surrounding_files(self, file_path: str) -> list[str]:
        """
        Get imports for a specific file.

        :param file_path: Path to the file
        :return: List of importers and imports
        """
        if not self.is_valid or not self.cache:
            return []

        importers: list[str] = self.cache.get("importers", {}).get(file_path, [])
        imports: list[str] = self.cache.get("imports", {}).get(file_path, [])

        return importers + imports


class ContextCache(BaseCache):
    """
    Cache for LLM context data.
    Stores formatted XML contexts for different context sizes.
    """

    def __init__(self):
        """
        Initialize the context cache.
        """
        self._large_context_xml: str = ""
        self._small_context_xml: str = ""
        self._bug_report_context: str = ""
        self._issue_context: str = ""
        self._timestamp: float = 0
        self._is_valid: bool = False

    def invalidate(self) -> None:
        """
        Invalidate the context cache.

        :return: None
        """
        self._is_valid = False

    @property
    def is_valid(self) -> bool:
        """
        Check if the context cache is valid.

        :return: True if valid, False otherwise
        """
        return self._is_valid

    def update_contexts(self, large_xml: str, small_xml: str) -> None:
        """
        Update the cached context XML for both context sizes.

        :param large_xml: Formatted XML for large context models
        :param small_xml: Formatted XML for small context models
        :return: None
        """
        self._large_context_xml = large_xml
        self._small_context_xml = small_xml
        self._issue_context = large_xml
        self._bug_report_context = small_xml
        self._timestamp = time.time()
        self._is_valid = True

    @property
    def large_context_xml(self) -> str:
        """
        Get the cached large context files XML.

        :return: XML string for large context
        """
        return self._large_context_xml if self._is_valid else ""

    @property
    def small_context_xml(self) -> str:
        """
        Get the cached small context files XML.

        :return: XML string for small context
        """
        return self._small_context_xml if self._is_valid else ""

    def update_large_context(self, large_xml: str) -> None:
        """
        Update just the large context XML.

        :param large_xml: Formatted XML for large context models
        :return: None
        """
        self._large_context_xml = large_xml
        self._issue_context = large_xml
        self._timestamp = time.time()
        self._is_valid = True

    def update_small_context(self, small_xml: str) -> None:
        """
        Update just the small context XML.

        :param small_xml: Formatted XML for small context models
        :return: None
        """
        self._small_context_xml = small_xml
        self._bug_report_context = small_xml
        self._timestamp = time.time()
        self._is_valid = True
