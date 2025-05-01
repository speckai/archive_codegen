import base64
import os
from io import BytesIO
from typing import TYPE_CHECKING, Any

from PIL import Image
from pydantic import BaseModel, Field
from src.agents.code_analyzer.utils.path_utils import absolute_path
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.file_read.prompt import PROMPT
from src.agents.implementer.utils.file_utils import (
    IMAGE_EXTENSIONS,
    MAX_OUTPUT_SIZE,
    add_line_numbers,
    find_similar_file,
    read_text_content,
)
from src.agents.implementer.utils.fs import (
    FileStats,
    exists,
    read_file_binary,
    stat,
)
from src.agents.implementer.utils.persistent_shell import get_persistent_shell
from src.utils.logging import logger

if TYPE_CHECKING:
    pass

MAX_WIDTH = 2000
MAX_HEIGHT = 2000
MAX_IMAGE_SIZE = 3.75 * 1024 * 1024  # 5MB in bytes, with base64 encoding


class FileReadInput(BaseModel):
    file_path: str = Field(..., description="The absolute path to the file to read")
    offset: int | None = Field(
        None,
        description="The line number to start reading from. Only provide if the file is too large to read at once",
    )
    limit: int | None = Field(
        None,
        description="The number of lines to read. Only provide if the file is too large to read at once.",
    )


class FileReadTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "View"

    @property
    def prompt(self):
        return PROMPT

    @property
    def input_schema(self):
        return FileReadInput

    @property
    def is_read_only(self):
        return True

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        file_path: str = input["file_path"]
        offset: int | None = input.get("offset")
        limit: int | None = input.get("limit")

        logger.debug(f"file_path: {file_path}")

        if not await exists(file_path):
            similar_file = await find_similar_file(file_path)
            message = "File does not exist."

            if similar_file:
                message += f" Did you mean {similar_file}?"

            return {
                "result": False,
                "message": message,
            }

        stats: FileStats = await stat(file_path)
        file_size: int = stats.st_size
        ext: str = os.path.splitext(file_path)[1].lower()

        if ext not in IMAGE_EXTENSIONS and (
            file_size > MAX_OUTPUT_SIZE and not offset and not limit
        ):
            return {
                "result": False,
                "message": self._format_file_size_error(file_size),
                "meta": {"fileSize": file_size},
            }

        return {"result": True, "model": FileReadInput}

    def _format_file_size_error(self, size_in_bytes: int) -> str:
        return f"File content ({size_in_bytes / 1024:.2f}KB) exceeds maximum allowed size ({MAX_OUTPUT_SIZE / 1024:.2f}KB). Please use offset and limit parameters to read specific portions of the file, or use the GrepTool to search for specific content."

    def create_image_response(self, image_data: bytes, ext: str) -> dict:
        mime_type: str = f"image/{ext[1:]}" if ext.startswith(".") else f"image/{ext}"
        return {
            "type": "image",
            "file": {
                "base64": base64.b64encode(image_data).decode("utf-8"),
                "type": mime_type,
            },
        }

    async def read_image(self, file_path: str, ext: str) -> dict:
        """Read and process an image file, resizing or compressing if needed"""
        try:
            abs_path: str = await absolute_path(
                get_persistent_shell().get_task(), file_path
            )
            stats: FileStats = await stat(abs_path)
            file_size: int = stats.st_size

            img_data: bytes = await read_file_binary(abs_path)

            if file_size <= MAX_IMAGE_SIZE:
                with Image.open(BytesIO(img_data)) as img:
                    width, height = img.size
                    if width <= MAX_WIDTH and height <= MAX_HEIGHT:
                        return self.create_image_response(img_data, ext)

            with Image.open(BytesIO(img_data)) as img:
                width, height = img.size

                if width > MAX_WIDTH:
                    height = int((height * MAX_WIDTH) / width)
                    width = MAX_WIDTH

                if height > MAX_HEIGHT:
                    width = int((width * MAX_HEIGHT) / height)
                    height = MAX_HEIGHT

                resized_img: Image.Image = img.resize(
                    (width, height), Image.Resampling.LANCZOS
                )

                output: BytesIO = BytesIO()

                if ext.lower() in {".jpg", ".jpeg"}:
                    resized_img.save(output, format="JPEG", quality=90)
                elif ext.lower() == ".png":
                    resized_img.save(output, format="PNG")
                elif ext.lower() == ".gif":
                    resized_img.save(output, format="GIF")
                elif ext.lower() == ".bmp":
                    resized_img.save(output, format="BMP")
                elif ext.lower() == ".webp":
                    resized_img.save(output, format="WEBP")
                else:
                    resized_img.save(output, format="JPEG", quality=90)
                    ext = ".jpeg"

                resized_data: bytes = output.getvalue()

                if len(resized_data) > MAX_IMAGE_SIZE:
                    output = BytesIO()
                    resized_img = (
                        resized_img.convert("RGB")
                        if resized_img.mode != "RGB"
                        else resized_img
                    )
                    resized_img.save(output, format="JPEG", quality=80)
                    return self.create_image_response(output.getvalue(), ".jpeg")

                return self.create_image_response(resized_data, ext)

        except Exception as e:
            try:
                img_data = await read_file_binary(abs_path)
                return self.create_image_response(img_data, ext)
            except Exception:
                return {"type": "error", "error": f"Failed to process image: {str(e)}"}

    async def call(
        self,
        input: FileReadInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        file_path: str = input.file_path
        offset: int = input.offset or 1
        limit: int | None = input.limit

        ext: str = os.path.splitext(file_path)[1].lower()

        logger.debug(f"Reading file: {file_path}")

        stats = await stat(file_path)
        context.read_file_timestamps[file_path] = stats.st_mtime

        if ext in IMAGE_EXTENSIONS:
            data: dict = await self.read_image(file_path, ext)
            return FullToolUseResult(
                data=data,
                result_for_assistant=self.render_result_for_assistant(data),
            )

        line_offset: int = 0 if offset <= 1 else offset - 1
        content, line_count, total_lines = await read_text_content(
            file_path, line_offset, limit
        )

        if len(content.encode("utf-8")) > MAX_OUTPUT_SIZE:
            return FullToolUseResult(
                result_for_assistant=self._format_file_size_error(
                    len(content.encode("utf-8"))
                ),
                data={"error": "File too large"},
            )

        logger.debug(f"content: {content[:100]}")
        data: dict = {
            "type": "text",
            "file": {
                "file_path": file_path,
                "content": content,
                "num_lines": line_count,
                "start_line": offset,
                "total_lines": total_lines,
            },
        }

        return FullToolUseResult(
            data=data,
            result_for_assistant=self.render_result_for_assistant(data),
        )

    def render_result_for_assistant(self, data: dict) -> str | list[dict]:
        if data["type"] == "image":
            return [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "data": data["file"]["base64"],
                        "media_type": data["file"]["type"],
                    },
                }
            ]
        if data["type"] == "text":
            return add_line_numbers(
                content=data["file"]["content"], start_line=data["file"]["start_line"]
            )

        return [data]
