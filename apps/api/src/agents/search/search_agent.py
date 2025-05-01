import time
from typing import TYPE_CHECKING

from src.agents.search.embeddings import Embeddings
from src.agents.utils.base_agent import BaseAgent
from src.agents.utils.debug.decorators import debug_agent_function
from src.prompts import RERANKER_SYSTEM_PROMPT, RERANKER_USER_PROMPT
from src.schemas.core.common import FileObject, FileSearchResult
from src.schemas.core.search import RerankedScore, RerankerResult, VectorDbSearchResult
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

PRUNE_RERANKER_RESULTS_THRESHOLD: float = 30.0
LIMIT_RESULTS: int = 10


class SearchAgent(BaseAgent):
    def __init__(self, task: "Task") -> None:
        """Initialize the SearchAgent with a task and embeddings."""
        super().__init__(task)
        self.embeddings: Embeddings = Embeddings(task=task)

    @debug_agent_function
    async def index_codebase(self) -> bool:
        tracked_file_paths: list[str] = (
            await self.task.file_system.get_all_tracked_file_paths()
        )

        await self.embeddings.prune_embeddings(tracked_file_paths)

        start_time = time.time()
        files: list[FileObject] = await self.task.file_system.get_all_tracked_files()
        num_indexed_chunks: int = await self.embeddings.update_embeddings(files)
        logger.success(
            f"Indexed {num_indexed_chunks} chunks ({len(tracked_file_paths)} files) in {time.time() - start_time} seconds"
        )
        return True

    @debug_agent_function
    async def search_codebase(
        self,
        search_query: str,
        override_files: list[FileObject] | None = None,
        reranker_prompt: str = None,
    ) -> list[FileSearchResult]:
        """Search the codebase based on the search query."""
        start_time = time.time()
        files: list[FileObject] = []
        if override_files is None:
            files = await self.task.file_system.get_all_tracked_files()
        else:
            assert all(
                isinstance(f, FileObject) for f in override_files
            ), "All items in override_files must be FileObject instances"
            files = override_files

        if not hasattr(self.task, "current_workflow"):
            logger.critical("Current task not set")
            logger.critical(self.task)

        change_and_components: str = search_query.strip()
        # if self.task.current_workflow.context.selected_components:
        #     # TODO: REDO THS
        #     change_and_components += "TEST"

        start_time = time.time()
        await self.embeddings.prune_embeddings([f.file_path for f in files])
        logger.info(f"Pruning embeddings took {time.time() - start_time} seconds")

        file_names, file_search_results = await self._get_codebase_search_results(
            change_and_components, files, reranker_prompt
        )
        logger.info(f"Search complete in {time.time() - start_time} seconds")
        return file_search_results

    async def _get_codebase_search_results(
        self, query: str, files: list[FileObject], reranker_prompt: str = None
    ) -> tuple[list[str], list[FileSearchResult]]:
        """Perform a search on the codebase and return ranked results."""
        start_time = time.time()
        initial_file_names: list[str] = []
        initial_results: list[VectorDbSearchResult] = []
        initial_file_names, initial_results = await self.embeddings.search_files(
            query, limit=LIMIT_RESULTS, files=files
        )
        # await self.send_update_data(
        #     MessageType.FILE_SEARCH_RESULTS, {"files": initial_file_names}
        # )
        logger.info(f"Vector search took {(time.time() - start_time):.2f} seconds")

        start_time = time.time()
        reranked_results: list[RerankedScore] = await self._rerank_results(
            query=query, search_results=initial_results, reranker_prompt=reranker_prompt
        )
        filtered_reranked_results: list[RerankedScore] = [
            result
            for result in reranked_results
            if result.score > PRUNE_RERANKER_RESULTS_THRESHOLD
        ]
        file_names: list[str] = list(
            {str(result.file_path) for result in filtered_reranked_results}
        )
        logger.info(f"Reranking took {time.time() - start_time} seconds")

        file_search_results: list[FileSearchResult] = []
        total_score_map: dict[str, float] = {}
        for score_obj in filtered_reranked_results:
            file_path = str(score_obj.file_path)
            if file_path not in total_score_map:
                total_score_map[file_path] = 0.0
            total_score_map[file_path] += score_obj.score

        for file_path, total_score in total_score_map.items():
            file_obj: FileObject = next(
                (f for f in files if f.file_path == file_path), None
            )
            if file_obj is None:
                # print all file names in files
                logger.error([f.file_path for f in files])
                logger.error(f"File {file_path} not found in files")
                continue
            file_search_results.append(
                FileSearchResult(
                    file_path=file_path,
                    content=file_obj.content,
                    total_score=total_score,
                )
            )

        file_search_results.sort(key=lambda x: x.total_score, reverse=True)
        return file_names, file_search_results

    async def _rerank_results(
        self,
        query: str,
        search_results: list[VectorDbSearchResult],
        reranker_prompt: str = None,
    ) -> list[RerankedScore]:
        """Rerank the search results based on their relevance to the query."""
        results_xml: str = "\n".join([result.xml for result in search_results])
        query = query if reranker_prompt is None else reranker_prompt

        reranked_results: RerankerResult = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=RERANKER_SYSTEM_PROMPT(),
            message=RERANKER_USER_PROMPT(
                objective=query,
                results=results_xml,
            ),
            response_model=RerankerResult,
        )
        pruned_results: list[RerankedScore] = reranked_results.scores[:LIMIT_RESULTS]

        return pruned_results
