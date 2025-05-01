from pathlib import Path

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str
    file_path: Path
    chunk_index: int
    starting_line: int
    ending_line: int


class VectorDbSearchResult(BaseModel):
    id: str
    chunk: Chunk
    similarity_score: float


class RerankedScore(BaseModel):
    thinking: str = Field(
        ...,
        description="Think step by step, describe your reasoning for choosing this score. Specifically cite lines of code, functions and files where applicable to back up your thought process.",
    )
    file_path: Path = Field(
        ...,
        description="The file path of the search result for file lookup.",
    )
    id: str = Field(
        ...,
        description="The id of the search result",
    )
    score: float = Field(
        ...,
        description="Score of relevancy of the result, between 0 and 100 that measures the relevance of the search result to the query",
    )


class RerankerResult(BaseModel):
    scores: list[RerankedScore] = Field(
        ...,
        description="List of scores, one per search result",
    )
