import asyncio
import hashlib
import re
from typing import TYPE_CHECKING, Optional, override

import tiktoken
from openai import OpenAI
from openai.types import CreateEmbeddingResponse
from qdrant_client import QdrantClient
from qdrant_client.conversions.common_types import PointId
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    ScoredPoint,
    VectorParams,
)
from src.agents.search.code_chunker import split_file
from src.config import OPENAI_API_KEY, QDRANT_API_KEY, QDRANT_URL
from src.schemas.core.common import FileObject
from src.schemas.core.search import Chunk, VectorDbSearchResult
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

EMBEDDING_MODEL: str = "text-embedding-3-large"


class EmbeddingGenerator:
    def __init__(self):
        self.batch_size: int = 2048
        self.dims: int = 3072
        self.max_tokens: int = 8100
        self.client: OpenAI = OpenAI(api_key=OPENAI_API_KEY)
        self.encoding = tiktoken.encoding_for_model(EMBEDDING_MODEL)
        # TODO: Add Azure OpenAI fallback

    def trim_length(self, text: str) -> str:
        """Trim text to max token length (8190) using tiktoken"""
        tokens = self.encoding.encode(text)
        if len(tokens) > self.max_tokens:  # Leave room for potential special tokens
            logger.critical(
                f"Trimmed text from {len(tokens)} tokens to {self.max_tokens}"
            )
            logger.critical(f"Original text: {text}")
            tokens = tokens[: self.max_tokens]
            text = self.encoding.decode(tokens)
        return text

    def create_embeddings_sync(self, texts: list[str]) -> list[list[float]]:
        processed_texts: list[str] = []
        for text in texts:
            tokens: list[int] = self.encoding.encode(text)
            if len(tokens) > self.max_tokens:
                chunks: list[str] = []
                for i in range(0, len(tokens), self.max_tokens):
                    chunk_tokens: list[int] = tokens[i : i + self.max_tokens]
                    chunk_text: str = self.encoding.decode(chunk_tokens)
                    chunks.append(chunk_text)
                processed_texts.extend(chunks)
            else:
                processed_texts.append(text)

        # Create batches based on token counts
        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_tokens: int = 0

        for text in processed_texts:
            text_tokens = len(self.encoding.encode(text))
            if current_tokens + text_tokens > self.max_tokens:
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = text_tokens
            else:
                current_batch.append(text)
                current_tokens += text_tokens

        if current_batch:  # Add the last batch if it exists
            batches.append(current_batch)

        all_embeddings: list[list[float]] = []
        for batch in batches:
            response: CreateEmbeddingResponse = self.client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL,
                dimensions=self.dims,
            )
            all_embeddings.extend([embedding.embedding for embedding in response.data])

        return all_embeddings


class Embeddings:
    @override
    def __init__(self, task: "Task") -> None:
        self.task: "Task" = task
        self.embedding_generator: EmbeddingGenerator = EmbeddingGenerator()

        self.qdrant_client: QdrantClient = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            prefer_grpc=False,
        )

        self.collection_name: str = self._get_collection_name()

    async def search_files(
        self,
        change_and_components: str,
        limit: int,
        files: list[FileObject] = None,
    ) -> tuple[list[str], list[VectorDbSearchResult]]:
        """Search for relevant files"""
        await self.update_embeddings(files)

        query_embedding: list[float] = (
            await self._create_embedding_with_fallback([change_and_components])
        )[0]

        results: list[ScoredPoint] = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
        )

        # Convert to VectorDbSearchResult format
        formatted_results: list[VectorDbSearchResult] = []
        temp_chunks: dict[str, list[Chunk]] = {}

        for hit in results:
            file_path: str = hit.payload["file_path"]
            chunk_index: int = hit.payload["chunk_index"]

            file: FileObject = next(
                (file for file in files if str(file.file_path) == file_path),
                None,
            )
            if not file:
                logger.warning(f"[Search] File {file_path} not found in files")
                continue

            if file_path not in temp_chunks:
                temp_chunks[file_path] = split_file(file_object=file)

            chunks: list[Chunk] = temp_chunks[file_path]
            chunk: Chunk = chunks[chunk_index]
            res: VectorDbSearchResult = VectorDbSearchResult(
                id=f"{file.file_path}:{chunk.starting_line}-{chunk.ending_line}",
                chunk=chunk,
                similarity_score=hit.score,
            )
            formatted_results.append(res)

        return (
            list({f.chunk.file_path for f in formatted_results}),
            formatted_results,
        )

    async def update_embeddings(self, files: list[FileObject]) -> int:
        """Update embeddings for changed files"""
        self._validate_collection_exists()
        stored_hashes: dict[str, str] = await self._get_stored_hashes()

        changes: list[tuple[FileObject, str]] = [
            (file, hashlib.sha256(file.content.encode()).hexdigest())
            for file in files
            if file.content.strip()  # Skip empty files
            and (
                str(file.file_path) not in stored_hashes
                or stored_hashes[str(file.file_path)]
                != hashlib.sha256(file.content.encode()).hexdigest()
            )
        ]

        if changes:
            changed_paths: list[str] = [str(file.file_path) for file, _ in changes]
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path", match=MatchAny(any=changed_paths)
                        )
                    ]
                ),
            )

        async def process_file(file: FileObject, file_hash: str) -> list[PointStruct]:
            chunks: list[Chunk] = split_file(file)
            if not chunks:
                return []

            chunk_texts: list[str] = [chunk.text for chunk in chunks]
            embeddings: list[list[float]] = await self._create_embedding_with_fallback(
                chunk_texts
            )

            def generate_stable_id(file_path: str, idx: int) -> int:
                unique_str = f"{file_path}:{idx}"
                hash_obj = hashlib.sha256(unique_str.encode())
                return int.from_bytes(hash_obj.digest()[:8], byteorder="big")

            return [
                PointStruct(
                    id=generate_stable_id(str(file.file_path), idx),
                    vector=embedding,
                    payload={
                        "file_path": str(file.file_path),
                        "chunk_index": idx,
                        "file_hash": file_hash,
                        "starting_line": chunk.starting_line,
                        "ending_line": chunk.ending_line,
                    },
                )
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ]

        tasks: list[asyncio.Coroutine[any, any, list[PointStruct]]] = [
            process_file(file, file_hash) for file, file_hash in changes
        ]
        points_lists: list[list[PointStruct]] = await asyncio.gather(*tasks)
        points: list[PointStruct] = [
            point for sublist in points_lists for point in sublist
        ]

        if points:
            self.qdrant_client.upload_points(
                collection_name=self.collection_name,
                points=points,
                parallel=8,
                max_retries=3,
            )
        return len(points)

    async def prune_embeddings(self, file_paths: list[str]) -> bool:
        """Delete all embeddings that are not in the tracked file paths and return number deleted"""
        self._validate_collection_exists()

        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must_not=[
                    FieldCondition(key="file_path", match=MatchAny(any=file_paths))
                ]
            ),
        )
        return True

    def _get_collection_name(self) -> str:
        """Generate collection name based on task info"""
        if self.task.debug:
            return "test_embeddings"

        base_name: str = (
            f"{self.task.user.name}_{self.task.git.repo_id}_{self.embedding_generator.dims}"
        )
        sanitized_name: str = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name)
        return sanitized_name

    def _validate_collection_exists(self) -> None:
        """Create collection if it doesn't exist"""
        collection_exists: bool = self.qdrant_client.collection_exists(
            self.collection_name
        )
        if collection_exists:
            return

        # TODO: Support SPLADE sparse vectors over dense vectors
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_generator.dims, distance=Distance.COSINE
            ),
        )

    async def _get_stored_hashes(self) -> dict[str, str]:
        """Get stored hashes for all files in the collection"""
        stored_hashes: dict[str, str] = {}
        offset: Optional[PointId] = None
        batch_size: int = 10000

        while True:
            batch: tuple[list[PointStruct], Optional[PointId]] = (
                self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    offset=offset,
                    limit=batch_size,
                    with_payload=["file_path", "file_hash"],
                    with_vectors=False,
                )
            )
            points, offset = batch
            stored_hashes.update(
                {
                    str(point.payload["file_path"]): point.payload["file_hash"]
                    for point in points
                }
            )

            if offset is None:
                break
        return stored_hashes

    async def _create_embedding_with_fallback(
        self, inputs: list[str]
    ) -> list[list[float]]:
        embeddings: list[list[float]] = await asyncio.to_thread(
            self.embedding_generator.create_embeddings_sync, inputs
        )
        return embeddings
