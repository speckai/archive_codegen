import asyncio
import time
from typing import TYPE_CHECKING

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from pydantic import BaseModel, Field
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common import FileObject, FileSearchResult
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

FILE_FILTER_SYSTEM_PROMPT = """You are a code search assistant. Your task is to determine if a file is relevant to a user's search query.
""".strip()

FILE_FILTER_USER_PROMPT = """
This is the current issue description of what's being solved. It's not directly addressed to you, but we're using it to determine if a file is relevant to implementing what is detailed in the issue description.
<user_search_query>
{query}
</user_search_query>

This is a tree to give you an idea of the context behind the the file that you're going to see.
<directory_tree>
{tree}
</directory_tree>

This is what you're actually evaluating wrt the query above.
<file_path>
{file_path}
</file_path>

This is the content of the file you're evaluating.
<file_content>
{file_content}
</file_content>

{referenced_file_notice}

Determine if this file is relevant to the search query.
We only want files that directly need to be edited in order to fulfill the user's search query OR is necessary to know about to implement the user's query. A downstream AI will implement the user's query based on the files you return.

For example, if the query includes "we need to add a like button to posts", relevant files would include:
- The UI component file/page where the like button needs to be added
- The API endpoint file needed for like functionality
- Example files showing how similar interaction buttons are implemented
- Hook files for state management
- Type definition files that need updating

Or if the query includes "we need to add image upload to profile", relevant files would include:
- The profile page/component that needs the upload UI
- The upload API endpoint
- Existing image upload components for reference
- Image processing utility files
- Upload configuration files

If a file references files that are relevant, that doesn't meant the file that we're looking at is relevant (ex. a config file that isn't necessary to know about but references the relevant files).

Do NOT include files that are:
- Only tangentially related
- Generic utilities that won't need modification/no relevant info
- "Nice to know" but not necessary for implementation

Remember: The goal is to provide the downstream AI with both the files that need changes AND the necessary reference implementations to understand the current patterns.

You'll also create a reduced representation of the file that will describe how it is relevant to the query. That includes a paragraph and parts of the code that the next engineer will look at. Include at least 10 lines of the code with ... in between parts that you truncate. Leave this blank if the file is not relevant.
""".strip()


class FileRelevanceResult(BaseModel):
    reasoning: str = Field(
        description="Explanation of why the file is or isn't relevant"
    )
    is_relevant: bool = Field(
        description="Whether the file is directly relevant to the search query"
    )
    score: float = Field(
        description="A score between 0 and 100 indicating the relevance of the file to the search query"
    )
    reduced_representation: str = Field(
        description="A condensed representation of the file highlighting the relevant parts for the search query and code snippets. Empty if not relevant file."
    )


class BruteSearchAgent(BaseAgent):
    def __init__(self, task: "Task"):
        super().__init__(task)

    async def search_codebase(
        self,
        search_query: str,
        referenced_files: list[str] | None = None,
        override_files: list[FileObject] | None = None,
        max_rounds: int = 3,
    ) -> list[tuple[FileSearchResult, FileRelevanceResult]]:
        """Search the codebase based on the search query."""
        start_time = time.time()

        # Get refined tree based on query
        refined_tree = await self.task.tree_agent.refine_tree(search_query, max_rounds)

        # Get files to search - either from override or from refined tree
        files = (
            override_files
            if override_files is not None
            else await self.task.file_system.get_all_tracked_files(
                use_repo_subdir=False
            )
        )

        # Filter files based on tree ignore patterns using proper gitignore matching
        if not override_files and refined_tree:
            spec = PathSpec.from_lines(
                GitWildMatchPattern, refined_tree.ignore_patterns
            )
            files = [
                file
                for file in files
                if not spec.match_file(file.file_path)
                or (referenced_files and file.file_path in referenced_files)
            ]

        # Get directory tree for context

        # Process each file with LLM to determine relevance
        relevant_files: list[tuple[FileSearchResult, FileRelevanceResult]] = []
        total_requests = 0

        # Create tasks for parallel processing
        async def process_file(
            file: FileObject,
        ) -> tuple[FileSearchResult, FileRelevanceResult]:
            # Add notice if file is referenced
            referenced_notice = (
                "\n<referenced_file_notice>This file has been referenced in previous conversations and is considered important context. Output it as relevant and give an accurate score.</referenced_file_notice>\n"
                if referenced_files and file.file_path in referenced_files
                else ""
            )

            filter_result = await self.llm_response(
                model_type=Model.GEMINI_2_0_FLASH_LITE,
                system=FILE_FILTER_SYSTEM_PROMPT,
                message=FILE_FILTER_USER_PROMPT.format(
                    query=search_query,
                    file_path=file.file_path,
                    referenced_file_notice=referenced_notice,
                    tree=refined_tree.tree_output,
                    file_content=(
                        f"{file.content[:50000]}..."
                        if len(file.content) > 50000
                        else file.content
                    ),
                ),
                response_model=FileRelevanceResult,
                log_tokens=True,
            )
            return file, filter_result

        # Process files in parallel
        tasks = [process_file(file) for file in files]
        results: list[tuple[FileObject, FileRelevanceResult]] = await asyncio.gather(
            *tasks
        )

        # Process results
        for file, filter_result in results:
            total_requests += 1

            if filter_result.is_relevant:
                relevant_files.append(
                    (
                        FileSearchResult(
                            file_path=file.file_path,
                            content=file.content,
                            total_score=filter_result.score,
                        ),
                        filter_result,
                    )
                )
                logger.debug(
                    f"File {file.file_path} relevant. Reason: {filter_result.reasoning}"
                )
            else:
                logger.debug(
                    f"File {file.file_path} not relevant. Reason: {filter_result.reasoning}"
                )
        logger.debug(f"Search complete in {time.time() - start_time} seconds")
        logger.debug(
            f"Made {total_requests} LLM requests to find {len(relevant_files)} relevant files"
        )
        return relevant_files
