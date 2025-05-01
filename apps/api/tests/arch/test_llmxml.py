from typing import Union

from llmxml import parse_xml
from pydantic import BaseModel, Field
from rich.console import Console


class RunCommandResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    command: str = Field(..., description="The final command")


class CreateFileResponse(BaseModel):
    thinking: str = Field(..., description="The assistant's analysis and reasoning")
    new_file_path: str = Field(..., description="The path to the new file")
    file_contents: str = Field(..., description="The full updated file contents")


class SectionEdit(BaseModel):
    original_code_section: str = Field(..., description="The original code section")
    new_code_section: str = Field(..., description="The new code section")


class FullFileContents(BaseModel):
    file_contents: str = Field(..., description="The full file contents to edit")


class EditFileResponse(BaseModel):
    thinking: str = Field(..., description="The thinking to perform")
    num_sections_to_modify: int = Field(
        ..., description="The number of sections to modify"
    )
    edits: list[Union[SectionEdit, FullFileContents]] = Field(
        ..., description="The inline_edits to make to the file"
    )


# Parse XML char by char
file_1 = "response_text_b2a38f17-c097-4d02-867c-3dca609da567.txt"
file_2 = "response_text_de1481af-e914-41bb-818a-cf0154f49517.txt"

# Both are create files
file_1_contents = open(file_1, "r").read()
file_2_contents = open(file_2, "r").read()

console = Console()
f1_prog = ""
for char in file_1_contents:
    f1_prog += char
    parsed = parse_xml(CreateFileResponse, f1_prog)
    # console.clear()
    # console.print(parsed)


f2_prog = ""
for char in file_2_contents:
    f2_prog += char
    parsed = parse_xml(CreateFileResponse, f2_prog)
    # console.clear()
    # console.print(parsed)
