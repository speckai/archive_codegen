from __future__ import annotations

import base64
import io
from typing import Any, Literal

from PIL import Image as PILImage
from pydantic import BaseModel, Field
from src.utils.prompt_utils import format_prompt


class FileObject(BaseModel):
    file_path: str = Field(description="Relative path to the file")
    content: str = Field(description="Content of the file")


class SelectedComponentParent(BaseModel):
    html_tag: str | None = None
    html_class_name: str | None = None
    html_children: str | None = None


class SelectedComponent(BaseModel):
    component_name: str | None
    file_path: str | None
    line_number: int | None
    no_component_info: bool = False
    html_tag: str | None = None
    html_class_name: str | None = None
    html_children: str | None = None
    parents: list[SelectedComponentParent] = []
    description: str | None = None  # Gemini-generated description

    @property
    def html_context(self) -> str:
        s = ""
        for parent in self.parents:
            if parent.html_tag:
                s += f"""<{parent.html_tag} class="{parent.html_class_name}">\n"""

        s += f"""<{self.html_tag} class="{self.html_class_name}">\n"""
        s += f"""{self.html_children}\n"""
        s += f"""</{self.html_tag}>\n"""

        for parent in self.parents[::-1]:
            if parent.html_tag:
                s += f"""</{parent.html_tag}>\n"""
        return s

    @property
    def requested_change_xml(self) -> str:
        return format_prompt(
            f"""
        <component_requested_change>
            <component_file_path>
                {self.file_path}
            </component_file_path>
            <user_requested_changes>
                {self.description}
            </user_requested_changes>
        </component_requested_change>
        """
        )

    @property
    def artifact_xml(self) -> str:
        """Returns formatted XML representation of this component with description for bug reports."""
        return f"""<component>
<id>component_1</id>
{
            f'''<html_tag>{self.html_tag}</html_tag>
<html_class_name>{self.html_class_name}</html_class_name>
<html_children>{self.html_children}</html_children>'''
            if self.no_component_info
            else f'''    <name>{self.component_name}</name>
<file_path>{self.file_path}</file_path>
<line_number>{self.line_number}</line_number>'''
        }
{f"<description>{self.description}</description>" if self.description else ""}
</component>
""".strip()


class FileSearchResult(BaseModel):
    file_path: str
    content: str
    total_score: float

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
        <file_search_result>
        <file_path>
        {self.file_path}
        </file_path>
        <content>
        {self.content}
        </content>
        </file_search_result>
        """
        )


class Image(BaseModel):
    name: str
    data: str  # Base64 object
    size: int
    source_url: str | None = None  # for screenshots
    annotation: str | None = None
    type: Literal["image/jpeg", "image/png", "image/webp"]  # force valid MIME types
    description: str | None = None  # Gemini-generated description

    @property
    def extension(self) -> str:
        """Returns the file extension from the MIME type."""
        return self.type.split("/")[-1]

    @property
    def source_url_length(self) -> int:
        """Returns length of source_url if it exists, 0 otherwise."""
        return len(self.source_url) if self.source_url else 0

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "source_url" and value and len(value) > 1000:
            raise ValueError("source_url cannot be longer than 1000 characters")
        super().__setattr__(name, value)

    def convert_to_webp(self) -> None:
        """
        Convert image to WebP format if it's currently PNG.
        Updates the data and type fields in-place.
        """
        if self.type == "image/webp":
            return

        base64_data = (
            self.data.split("base64,")[-1] if "base64," in self.data else self.data
        )

        image_data = base64.b64decode(base64_data)

        with io.BytesIO(image_data) as input_buffer:
            pil_image = PILImage.open(input_buffer)

            output_buffer = io.BytesIO()
            pil_image.save(output_buffer, format="WEBP", quality=85)
            output_buffer.seek(0)

            webp_data = output_buffer.getvalue()

        self.data = base64.b64encode(webp_data).decode("utf-8")
        self.type = "image/webp"
        self.size = len(webp_data)

    def ensure_webp(self) -> None:
        """Ensures the image is in WebP format, converting if necessary."""
        if self.type == "image/png":
            self.convert_to_webp()

    @property
    def data_bytes(self) -> bytes:
        """Returns the data as bytes. So we can save to cloud n stuff"""
        return base64.b64decode(self.data)

    def openai_dict_format(self, idx: int | str) -> list[dict]:
        self.ensure_webp()

        message_parts: list[dict] = [
            {
                "type": "text",
                "text": f"Image ID {idx if isinstance(idx, int) else idx}:"
                + (
                    f"\nUser Annotation: '{self.annotation}'"
                    + (f" for url {self.source_url}" if self.source_url else "")
                    if self.annotation
                    else ""
                ),
            }
        ]
        message_parts.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.type};base64,{self.data}",
                },
            }
        )

        return message_parts

    def openai_dict_format_without_id(self) -> list[dict]:
        self.ensure_webp()

        message_parts: list[dict] = []

        if self.annotation:
            message_parts.append(
                {
                    "type": "text",
                    "text": (
                        f"Annotation: {self.annotation}"
                        + (f" for url {self.source_url}" if self.source_url else "")
                    ),
                }
            )

        message_parts.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.type};base64,{self.data}",
                },
            }
        )

        return message_parts

    def anthropic_dict_format(self, idx: int | str) -> list[dict]:
        self.ensure_webp()

        message_parts = [
            {
                "type": "text",
                "text": f"Image ID {idx if isinstance(idx, int) else idx}:"
                + (
                    f"\nAnnotation: {self.annotation}"
                    + (f" for url {self.source_url}" if self.source_url else "")
                    if self.annotation
                    else ""
                ),
            }
        ]

        # Get the raw base64 data by removing any data URI prefix
        base64_data = (
            self.data.split("base64,")[-1] if "base64," in self.data else self.data
        )

        message_parts.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.type,
                    "data": base64_data,
                },
            }
        )

        return message_parts

    @property
    def artifact_xml(self) -> str:
        """Returns formatted XML representation of this image with description for bug reports."""
        screenshot_id = (
            f"screenshot_{self.name}"
            if not self.name.startswith("screenshot_")
            else self.name
        )

        xml_parts = []
        xml_parts.append(f"<id>{screenshot_id}</id>")
        if self.source_url:
            xml_parts.append(f"<url>{self.source_url}</url>")
        if self.annotation:
            xml_parts.append(f"<annotation>{self.annotation}</annotation>")
        if self.description:
            xml_parts.append(f"<description>{self.description}</description>")

        return f"""<screenshot>
{"\n".join(xml_parts)}
</screenshot>
""".strip()


class Video(BaseModel):
    name: str
    data: str  # Base64 encoded video data
    size: int
    source_url: str | None = None
    annotation: str | None = None
    type: Literal["video/webm"]
    description: str | None = None

    def openai_dict_format(self, idx: int | str) -> list[dict]:
        message_parts: list[dict] = [
            {
                "type": "text",
                "text": f"Video ID {idx}:"
                + (
                    f"\nUser Annotation: '{self.annotation}'"
                    + (f" for url {self.source_url}" if self.source_url else "")
                    if self.annotation
                    else ""
                ),
            }
        ]
        message_parts.append(
            {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{self.type};base64,{self.data}",
                },
            }
        )

        return message_parts

    def openai_dict_format_without_id(self) -> list[dict]:
        message_parts: list[dict] = []

        if self.annotation:
            message_parts.append(
                {
                    "type": "text",
                    "text": (
                        f"Annotation: {self.annotation}"
                        + (f" for url {self.source_url}" if self.source_url else "")
                    ),
                }
            )

        message_parts.append(
            {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{self.type};base64,{self.data}",
                },
            }
        )

        return message_parts

    @property
    def artifact_xml(self) -> str:
        """Returns formatted XML representation of this video with description for bug reports."""
        video_id = (
            f"video_{self.name}" if not self.name.startswith("video_") else self.name
        )

        xml_parts = []
        xml_parts.append(f"<id>{video_id}</id>")
        if self.source_url:
            xml_parts.append(f"<url>{self.source_url}</url>")
        if self.annotation:
            xml_parts.append(f"<annotation>{self.annotation}</annotation>")
        if self.description:
            xml_parts.append(f"<description>{self.description}</description>")

        return f"""<video>
{"\n".join(xml_parts)}
</video>
""".strip()


class ProjectDependencies(BaseModel):
    dependencies: dict[str, str]
    dev_dependencies: dict[str, str]

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
        <package_json_dependencies>
        <dependencies>
        {"\n".join([f"{key}: {value}" for key, value in self.dependencies.items()])}
        </dependencies>
        <dev_dependencies>
        {"\n".join([f"{key}: {value}" for key, value in self.dev_dependencies.items()])}
        </dev_dependencies>
        </package_json_dependencies>
        """
        )
