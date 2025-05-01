from typing import TYPE_CHECKING

from src.agents.code_analyzer.utils.file_io import read_files_into_fileinfo
from src.agents.code_analyzer.utils.import_relationships import ImportFinder
from src.agents.recording_bug_report.utils.file_formatter import format_files_context
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common.files import FileObject
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

SMALL_CONTEXT_LIMIT: int = 4


class CodeAnalyzerAgent(BaseAgent):
    """
    Collects related files by traversing imports/exports (via BFS).
    """

    def __init__(self, task: "Task"):
        """
        Initialize CodeAnalyzerAgent.

        :param task: The task object that provides access to chat, filesystem, etc.
        """
        super().__init__(task)
        self.task: "Task" = task
        self.import_finder: ImportFinder = ImportFinder(task)
        self.referenced_files: dict[str, None] = {}  # Ordered set of referenced files

    def invalidate_all_caches(self) -> None:
        """
        Invalidate all caches when repository changes.

        :return: None
        """
        self.import_finder.invalidate_cache()
        logger.debug("All code analyzer caches invalidated")

    def add_referenced_file(self, file_path: str) -> None:
        """
        Add file to the list of referenced files.

        :param file_path: Path of the file to add
        :return: None
        """
        self.referenced_files[file_path] = None

    async def get_relevant_files_xml(self, remaining_tokens: int) -> str:
        """
        Prepares and returns context for large context models (e.g., Claude).
        Regenerates the context each time.

        :return: XML-formatted large context
        """
        try:
            files: list[str] = list(self.referenced_files.keys())
            # go through all the files and add them until we're at the token limit
            large_context_files: list[FileObject] = await read_files_into_fileinfo(
                self.task, set(files)
            )
            current_tokens: int = 0
            # First check how many tokens we have from initial files
            for file in large_context_files:
                current_tokens += (
                    self.task.recording_bug_report_agent.token_counter.estimate_tokens(
                        file.content
                    )
                )
                if current_tokens > remaining_tokens:
                    break

            # If we haven't hit the limit, do BFS to find more related files
            if current_tokens < remaining_tokens:
                additional_files = set()
                for file_path in files:
                    related_files = await self.import_finder.get_imports(file_path)
                    additional_files.update(related_files)

                if additional_files := additional_files - set(files):
                    additional_context_files = await read_files_into_fileinfo(
                        self.task, additional_files
                    )
                    large_context_files.extend(additional_context_files)

            large_context_xml: str = format_files_context(
                large_context_files,
                max_tokens=remaining_tokens,
                token_counter=self.task.recording_bug_report_agent.token_counter,
            )

            return large_context_xml
        except Exception as e:
            logger.error(f"Error preparing large context: {str(e)}")
            return ""
