from pydantic import BaseModel, Field


class FileLocation(BaseModel):
    path: str = Field(description="Path to the file")
    from_line: int = Field(description="Starting line number")
    to_line: int = Field(description="Ending line number")


class StructuredConsoleLogInfo(BaseModel):
    reasoning: str = Field(
        description="Reasoning about the relevance of the files to the console logs"
    )
    relevant_files: list[FileLocation] = Field(
        description="List of file locations that appear to be relevant based on console logs"
    )
    keywords: list[str] = Field(
        description="List of non-library function names and variable names extracted from console logs that would be useful for searching the codebase. Only includes terms that would help locate relevant code without false positives."
    )
