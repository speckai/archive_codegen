import math
import re

import psutil
from src.schemas.core.common import FileObject
from src.schemas.core.search import Chunk


def _is_semantic_new_match(line: str) -> bool:
    patterns: list[str] = [
        r"\n\s*class.*?\{",  # Class declarations
        r"\n\s*return\s*\(",  # JSX return statements
    ]
    split_pattern: str = "|".join(patterns)
    return bool(re.search(split_pattern, line))


def split_file(file_object: FileObject) -> list[Chunk]:
    file_text: str = file_object.content

    MIN_CHUNK_SIZE: int = 50
    MAX_CHUNK_SIZE: int = 1000  # characters

    chunk_list: list[Chunk] = []
    chunk_index: int = 0
    all_lines: list[str] = file_text.split("\n")
    line_count: int = len(all_lines)
    idx: int = 0

    overlap: int = 50  # Number of characters to overlap

    while idx < line_count:
        starting_line: int = max(idx - 3, 0)
        cur_chunk_size: int = 0
        chunk_lines: list[str] = []

        while idx < line_count:
            cur_line: str = all_lines[idx]
            new_chunk_size: int = cur_chunk_size + len(cur_line)

            if cur_chunk_size != 0:
                if new_chunk_size > MAX_CHUNK_SIZE:
                    break
                if cur_chunk_size > MIN_CHUNK_SIZE and _is_semantic_new_match(cur_line):
                    break

            chunk_lines.append(cur_line)
            idx += 1
            cur_chunk_size = new_chunk_size

        # Add overlapping lines from the next chunk
        overlap_lines: list[str] = []
        overlap_size: int = 0
        while idx < line_count and overlap_size < overlap:
            overlap_lines.append(all_lines[idx])
            overlap_size += len(all_lines[idx])
            idx += 1

        chunk_lines.extend(overlap_lines)

        chunk: Chunk = Chunk(
            text="\n".join(chunk_lines),
            file_path=file_object.file_path,
            chunk_index=chunk_index,
            starting_line=starting_line,
            ending_line=idx - 1,
        )
        chunk_list.append(chunk)
        chunk_index += 1

        # Move the index back by the number of overlapping lines
        idx -= len(overlap_lines)

    return chunk_list


def calculate_optimal_batch_size(
    chunk_size: int = 1000,
    max_memory_usage: float = 0.1,
    min_batch_size: int = 1,
    max_batch_size: int = 32,
    safety_factor: float = 0.8,
) -> int:
    """Calculate the optimal batch size based on available system memory and other factors."""
    available_memory = psutil.virtual_memory().available
    max_batch_memory = available_memory * max_memory_usage

    # Calculate theoretical max batch size
    theoretical_max = max_batch_memory // chunk_size

    # Apply safety factor
    safe_batch_size = math.floor(theoretical_max * safety_factor)

    # Ensure batch size is within allowed range
    optimal_batch_size = max(min_batch_size, min(safe_batch_size, max_batch_size))

    return optimal_batch_size
