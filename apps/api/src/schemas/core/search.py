from pathlib import Path

from pydantic import BaseModel, Field
from src.utils.prompt_utils import format_prompt


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

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
        <search_result>
        <chunk_id>
        {self.id}
        </chunk_id>
        <chunk_info>
            <file_path>
            {self.chunk.file_path}
            </file_path>
            <content>
            {self.chunk.text}
            </content>
        </chunk_info>
        <vector_similarity_score>
        {self.similarity_score}
        </vector_similarity_score>
        </search_result>
            """
        )


class FileChange(BaseModel):
    file_path: str
    removed: bool
    hash: str


class RerankedScore(BaseModel):
    thinking: str = Field(
        ...,
        description="Consisely think step by step, describe your reasoning for choosing this score. Specifically cite lines of code, functions and files where applicable to back up your thought process.",
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
    thinking: str = Field(
        ...,
        description="Consisely think step by step, describe your reasoning for choosing these scores. Specifically cite lines of code, functions and files where applicable to back up your thought process.",
    )
    scores: list[RerankedScore] = Field(
        ...,
        description="List of scores, one per search result",
    )
