"""
Asset storage system for bug report assets.

Provides a wrapper around storage.py for storing and retrieving bug report assets,
including images, videos, and other artifacts referenced in bug reports.
"""

import base64
import os
import re
import subprocess
import tempfile
import traceback
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urlparse

import requests
from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.agents.code_analyzer.utils.reference_tracking import parse_markdown_links
from src.schemas.core.common import (
    ArtifactType,
    ComponentSelectionArtifact,
    ConsoleLogArtifact,
    RecordingArtifact,
    ReportAssetModel,
    ReproductionStepsArtifact,
    ScreenshotArtifact,
    VideoSegmentArtifact,
)
from src.utils.logging import logger
from src.utils.storage import save_asset

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class AssetStorage:
    """
    Handles storage and retrieval of assets for bug reports and issue descriptions.
    Maintains state of processed assets to avoid duplication when handling multiple contents.
    """

    def __init__(self, task: "Task"):
        """
        Initialize the asset storage.

        :param task: The task object this storage belongs to
        :return: None
        """
        self.task = task
        self.task_id = task.task_id or "test"
        self.asset_urls: dict[str, str] = {}
        self.text_models: dict[str, ReportAssetModel] = {}

    async def store_assets(
        self, content: str, artifacts: list[RecordingArtifact]
    ) -> tuple[str, dict[str, str], dict[str, ReportAssetModel]]:
        """
        Process content to store multimedia assets and update references.
        Works consistently for any markdown content with artifact or file references.
        Maintains state between calls to avoid reprocessing the same assets.

        :param content: The content in markdown format
        :param artifacts: List of recording artifacts referenced
        :return: Tuple of (updated content, asset URLs dict, text models dict)
        """
        logger.debug("Storing content assets")

        for artifact in artifacts:
            if (
                artifact.id not in self.asset_urls
                and artifact.id not in self.text_models
            ):
                await self._process_artifact(artifact)
            else:
                logger.debug(f"Skipping already processed artifact {artifact.id}")

        processed_content: str = await self._process_markdown_references(content)

        await self._process_file_references(content)

        logger.debug(
            f"Processed content with {len(self.asset_urls)} multimedia assets and {len(self.text_models)} text-based assets"
        )

        return processed_content, self.asset_urls, self.text_models

    async def store_image(self, image_data: bytes, filename: str) -> str:
        """
        Store an image and return its URL.
        """
        assert isinstance(image_data, bytes), "Image data must be bytes"
        return await save_asset(
            f"bug-reports/{self.task_id}/images", filename, image_data
        )

    async def convert_webm_to_gif(self, webm_url: str) -> tuple[str, str]:
        """
        Convert a webm video to gif format and upload it to storage.
        Maintains the same fps and resolution as the original video.

        :param webm_url: URL of the webm video to convert
        :return: Tuple of (gif_url, webm_url)
        """
        parsed_url: ParseResult = urlparse(webm_url)
        filename: str = os.path.basename(parsed_url.path)
        base_filename: str = filename.replace(".webm", "")
        gif_filename: str = f"{base_filename}.gif"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                webm_path: str = os.path.join(temp_dir, filename)
                response: requests.Response = requests.get(webm_url, stream=True)
                response.raise_for_status()

                with open(webm_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                gif_path: str = os.path.join(temp_dir, gif_filename)
                cmd: list[str] = [
                    "ffmpeg",
                    "-i",
                    webm_path,
                    "-vf",
                    "fps=10",
                    "-c:v",
                    "gif",
                    gif_path,
                ]

                process: subprocess.CompletedProcess = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr.decode()}")
                    return webm_url, webm_url

                with open(gif_path, "rb") as f:
                    gif_data: bytes = f.read()

                gif_url: str = await save_asset(
                    f"bug-reports/{self.task_id}/videos", gif_filename, gif_data
                )

                logger.debug(f"Converted and uploaded gif: {gif_url}")
                return gif_url, webm_url

        except Exception as e:
            logger.error(f"Error converting webm to gif: {str(e)}")
            logger.error(traceback.format_exc())
            return webm_url, webm_url

    async def _process_file_references(self, markdown_content: str) -> set[str]:
        """
        Extract file references from markdown content and update code analyzer weights.
        Ignores artifact IDs and external URLs.

        :param markdown_content: Markdown content with potential file references
        :return: Set of found file paths
        """
        file_paths, _ = parse_markdown_links(markdown_content)
        found_files = set()

        for file_path in file_paths:
            if any(f"{t.value}_" in file_path for t in ArtifactType):
                logger.debug(f"Skipping artifact reference: {file_path}")
                continue

            if file_path.startswith(("http://", "https://", "www.")):
                logger.debug(f"Skipping URL: {file_path}")
                continue
            try:
                normalized_path = await normalize_path(self.task, file_path)
                found_files.add(normalized_path)

                self.task.code_analyzer_agent.add_referenced_file(normalized_path)
            except Exception as e:
                logger.warning(f"Error processing file path '{file_path}': {str(e)}")

        self.task.code_analyzer_agent.invalidate_all_caches()

        return found_files

    async def _process_artifact(self, artifact: RecordingArtifact) -> None:
        """
        Process a single artifact based on its type.

        :param artifact: The artifact to process
        :return: None
        """
        if isinstance(artifact, VideoSegmentArtifact):
            await self._store_video_artifact(artifact)
        elif isinstance(artifact, ScreenshotArtifact):
            await self._store_screenshot_artifact(artifact)
        elif isinstance(artifact, ComponentSelectionArtifact):
            await self._store_component_selection_artifact(artifact)
        elif isinstance(artifact, (ConsoleLogArtifact, ReproductionStepsArtifact)):
            await self._store_text_artifact(artifact)
        else:
            logger.debug(f"Unknown artifact type: {artifact.artifact_type}")

        logger.debug(
            f"Processed artifact {artifact.id} of type {artifact.artifact_type}"
        )

    async def _store_video_artifact(self, artifact: VideoSegmentArtifact) -> str:
        """
        Store a video artifact and return its URL.

        :param artifact: The VideoSegmentArtifact to store
        :return: URL where the artifact is stored
        """
        artifact_id: str = artifact.id
        url: str = ""

        if artifact.video_data:
            url = await save_asset(
                f"bug-reports/{self.task_id}/videos",
                f"{artifact_id}.webm",
                base64.b64decode(artifact.video_data),
            )
        else:
            self.text_models[artifact_id] = ReportAssetModel(
                artifact_id=artifact_id,
                content_type="video_placeholder",
                markdown_format="text",
                data={
                    "title": artifact.title,
                    "description": artifact.description or "No description provided",
                    "start_time": artifact.start_time,
                    "end_time": artifact.end_time,
                    "duration": (artifact.end_time - artifact.start_time) / 1000.0,
                },
            )
            return ""

        if url:
            self.asset_urls[artifact_id] = url
            logger.debug(f"Stored video artifact {artifact_id} at {url}")

        url = url.replace(".webm", ".mp4")  # Github doesn't like .webm

        return url

    async def _store_screenshot_artifact(self, artifact: ScreenshotArtifact) -> str:
        """
        Store a screenshot artifact and return its URL.

        :param artifact: The ScreenshotArtifact to store
        :return: URL where the artifact is stored
        """
        artifact_id = artifact.id
        url = ""

        if artifact.image_data:
            try:
                base64_data = artifact.image_data.data

                image_data = base64.b64decode(base64_data)

                url = await save_asset(
                    f"bug-reports/{self.task_id}/screenshots",
                    f"{artifact_id}.{artifact.image_data.type.split('/')[-1]}",
                    image_data,
                )

            except Exception as e:
                logger.error(f"Error storing screenshot: {str(e)}")

                self.text_models[artifact_id] = ReportAssetModel(
                    artifact_id=artifact_id,
                    content_type="screenshot_placeholder",
                    markdown_format="text",
                    data={
                        "title": artifact.title,
                        "description": artifact.description
                        or "Screenshot (data unavailable)",
                        "annotation": artifact.annotation or "",
                    },
                )
                return ""
        else:
            # For screenshots without data, create a model
            self.text_models[artifact_id] = ReportAssetModel(
                artifact_id=artifact_id,
                content_type="screenshot_placeholder",
                markdown_format="text",
                data={
                    "title": artifact.title,
                    "description": artifact.description
                    or "Screenshot (data unavailable)",
                    "annotation": artifact.annotation or "",
                },
            )
            return ""

        if url:
            self.asset_urls[artifact_id] = url
            logger.debug(f"Stored screenshot artifact {artifact_id} at {url}")

        return url

    async def _store_component_selection_artifact(
        self, artifact: ComponentSelectionArtifact
    ) -> str:
        """
        Store a component selection artifact.
        If it has a screenshot, store that; otherwise store as a text model.

        :param artifact: The ComponentSelectionArtifact to store
        :return: URL where the artifact is stored, if applicable
        """
        artifact_id = artifact.id
        url = ""

        if artifact.image_data:
            try:
                base64_data = artifact.image_data.data

                image_data = base64.b64decode(base64_data)

                url = await save_asset(
                    f"bug-reports/{self.task_id}/components",
                    f"{artifact_id}.{artifact.image_data.type.split('/')[-1]}",
                    image_data,
                )
            except Exception as e:
                logger.error(f"Error storing component screenshot: {str(e)}")

        component_data = {}
        if (
            hasattr(artifact.component, "component_name")
            and artifact.component.component_name
        ):
            component_data = {
                "component_name": artifact.component.component_name,
                "file_path": artifact.component.file_path,
                "line_number": artifact.component.line_number,
            }
        else:
            component_data = {
                "html_tag": artifact.component.html_tag,
                "html_class_name": artifact.component.html_class_name,
                "html_children": artifact.component.html_children,
            }

        # Create the model
        self.text_models[artifact_id] = ReportAssetModel(
            artifact_id=artifact_id,
            content_type="component",
            markdown_format="html",
            data={
                "title": artifact.title,
                "description": artifact.description or "Component selection",
                "annotation": artifact.annotation or "",
                "component": component_data,
                "has_image": bool(url),
            },
        )

        if url:
            self.asset_urls[artifact_id] = url
            logger.debug(f"Stored component selection artifact {artifact_id} at {url}")

        return url

    async def _store_text_artifact(self, artifact: RecordingArtifact) -> None:
        """
        Store a text-based artifact as a structured model.

        :param artifact: The text-based artifact to process
        :return: None
        """
        artifact_id = artifact.id

        if isinstance(artifact, ConsoleLogArtifact):
            self.text_models[artifact_id] = ReportAssetModel(
                artifact_id=artifact_id,
                content_type="console_log",
                markdown_format="markdown",
                data=artifact.model_dump(),
            )
        elif isinstance(artifact, ReproductionStepsArtifact):
            self.text_models[artifact_id] = ReportAssetModel(
                artifact_id=artifact_id,
                content_type="reproduction_steps",
                markdown_format="markdown",
                data=artifact.model_dump(),
            )

        logger.debug(f"Stored text artifact {artifact_id} as model")

    async def _process_markdown_references(self, markdown_content: str) -> str:
        """
        Process markdown content to replace references with the appropriate representation.
        Extracts the H1 title and returns both title and processed content with the title removed.

        For multimedia artifacts: Replace with direct URLs
        For text artifacts: Keep the references for frontend processing

        :param markdown_content: Original markdown content with artifact references
        :return: Tuple of (title, processed_content without title)
        """
        artifact_pattern: str = "|".join([f"{t.value}_[a-z0-9]+" for t in ArtifactType])
        pattern: str = rf"(!?\[.*?\])\(({artifact_pattern})\)"

        def replace_reference(match: re.Match) -> str:
            text_part = match[1]
            artifact_id = match[2]

            if artifact_id in self.asset_urls:
                return f"{text_part}({self.asset_urls[artifact_id]})"
            elif artifact_id in self.text_models:
                return f"{text_part}({artifact_id})"
            else:
                logger.warning(f"Reference to unknown artifact ID: {artifact_id}")
                return match[0]

        processed_content: str = re.sub(pattern, replace_reference, markdown_content)

        return processed_content
