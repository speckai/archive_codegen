"""
Artifact manager for the initial context agent.
Provides centralized handling of artifacts (recordings, screenshots, components).
"""

import asyncio
from typing import TYPE_CHECKING

from src.agents.recording_bug_report.utils.artifact_filtering import filter_artifacts
from src.agents.recording_bug_report.utils.recording_artifact_extractor import (
    extract_replay_artifacts,
)
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common.recordings import (
    ComponentSelectionArtifact,
    ConsoleLogArtifact,
    RecordingArtifact,
    ReplayResponse,
    ScreenshotArtifact,
    VideoSegmentArtifact,
)
from src.schemas.llm import Model
from src.utils.llm.calls import analyze_video
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

SCREENSHOT_SYSTEM_PROMPT = """
You are a specialized assistant that describes screenshots in a concise, informative way.
Your descriptions focus on what is visually apparent in the image, emphasizing elements
that could be important for understanding bugs or issues in a user interface.
""".strip()

SCREENSHOT_USER_PROMPT = """
Please describe this screenshot from a user interface. Focus on:

1. What page or section of the application is shown
2. Any visible UI elements that appear important
3. Any obvious errors, warnings, or unusual states
4. The general state of the interface (loading, error, empty, etc.)

Keep your description concise (1-3 sentences) but informative.
""".strip()

COMPONENT_SYSTEM_PROMPT = """
You are a specialized assistant that describes UI components in bug reports.
""".strip()

COMPONENT_USER_PROMPT = """
Describe this UI component selected by the user:

<component>
{component_info}
</component>

Please provide a concise description of this UI component, focusing on:
1. What type of UI element this is (button, input field, etc.)
2. What function it likely serves in the application
3. Any clues about why the user might have selected or annotated this component

Keep it brief but informative for a bug report context.
""".strip()


class ArtifactManager(BaseAgent):
    """Manages artifact annotations and context generation for recordings, screenshots, and components."""

    def __init__(self, task: "Task"):
        """
        Initialize the artifact manager.

        :param task: The task object this manager belongs to
        :return: None
        """
        super().__init__(task)
        self.artifact_annotations: dict[str, str] = {}
        self._artifact_context: str = ""
        self._artifacts_changed: bool = True
        self.all_annotated_artifacts: list[RecordingArtifact] = []
        self.relevant_artifacts: list[RecordingArtifact] = []

    @property
    def artifact_context(self) -> str:
        """
        Get formatted artifact context XML, rebuilding if needed.
        Uses the relevant_artifacts list for generating context.

        :return: Formatted artifact context as XML string
        """
        return self._artifact_context

    def invalidate_cache(self) -> None:
        """
        Mark artifacts as changed, requiring regeneration of context.

        :return: None
        """
        self._artifacts_changed = True

    async def process_replay_artifacts(
        self,
        replay: ReplayResponse,
    ) -> list[RecordingArtifact]:
        """
        Processes a recording to extract artifacts.
        Populates both all_annotated_artifacts and relevant_artifacts collections.

        :param replay: The replay response to process
        :return: List of relevant extracted and annotated artifacts
        """
        logger.debug(
            f"Processing recording artifacts for recording {replay.recording.name}"
        )

        artifacts: list[RecordingArtifact] = await extract_replay_artifacts(replay)

        self.all_annotated_artifacts = await self._annotate_recording_artifacts(
            artifacts
        )

        self.relevant_artifacts = await filter_artifacts(
            self.all_annotated_artifacts, replay
        )

        logger.debug(
            f"Filtered from {len(self.all_annotated_artifacts)} to {len(self.relevant_artifacts)} artifacts"
        )
        self.invalidate_cache()
        return self.relevant_artifacts

    async def _annotate_recording_artifacts(
        self, artifacts: list[RecordingArtifact]
    ) -> list[RecordingArtifact]:
        """
        Annotates recording artifacts with additional context using LLM.

        :param artifacts: List of recording artifacts to annotate
        :return: List of annotated recording artifacts
        """
        console_artifacts = [a for a in artifacts if isinstance(a, ConsoleLogArtifact)]
        video_artifacts = [a for a in artifacts if isinstance(a, VideoSegmentArtifact)]
        screenshot_artifacts = [
            a for a in artifacts if isinstance(a, ScreenshotArtifact)
        ]
        component_artifacts = [
            a for a in artifacts if isinstance(a, ComponentSelectionArtifact)
        ]

        artifact_tasks: list[RecordingArtifact] = []

        for artifact in console_artifacts:
            artifact_tasks.append(self._annotate_console_log_artifact(artifact))

        for artifact in video_artifacts:
            artifact_tasks.append(self._annotate_video_segment_artifact(artifact))

        for artifact in screenshot_artifacts:
            artifact_tasks.append(self._annotate_screenshot_artifact(artifact))

        for artifact in component_artifacts:
            artifact_tasks.append(self._annotate_component_artifact(artifact))

        logger.debug(f"Annotating {len(artifact_tasks)} recording artifacts")
        results: list[RecordingArtifact] = await asyncio.gather(
            *[task for task in artifact_tasks]
        )

        return results

    async def _annotate_console_log_artifact(
        self, artifact: ConsoleLogArtifact
    ) -> ConsoleLogArtifact:
        """
        Generates a description for a console log artifact.

        :param artifact: The console log artifact to annotate
        :return: Description string for the artifact
        """

        prompt = f"""
Analyze this console log and provide:
1. A short description of what is happening
2. An error type classification
3. A severity assessment (low, medium, high)

<console_log>
{artifact.xml}
</console_log>
""".strip()

        artifact.description = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system="You are a helpful assistant that analyzes console logs.",
            message=prompt,
            response_model=str,
        )

        return artifact

    async def _annotate_video_segment_artifact(
        self, artifact: VideoSegmentArtifact
    ) -> VideoSegmentArtifact:
        """
        Generates a description for a video segment artifact.

        :param artifact: The video segment artifact to annotate
        :return: Description string for the artifact
        """

        text_prompt: str = f"""
Describe this video segment from a user recording:

Title: {artifact.title}
Start time: {artifact.start_time}ms
End time: {artifact.end_time}ms

Please provide a concise description of what this video segment shows, focusing on what would be most relevant for a bug report.
""".strip()

        artifact.description = analyze_video(text_prompt, artifact.video_data)

        return artifact

    async def _annotate_screenshot_artifact(
        self, artifact: ScreenshotArtifact
    ) -> ScreenshotArtifact:
        """
        Generates a description for a screenshot artifact using vision model.

        :param artifact: The screenshot artifact to annotate
        :return: Description string for the artifact
        """
        content = [
            {
                "type": "text",
                "text": SCREENSHOT_USER_PROMPT.format(
                    current_artifact_state=artifact.xml
                ),
            }
        ]
        content.extend(artifact.image_data.openai_dict_format(0))

        artifact.description = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=SCREENSHOT_SYSTEM_PROMPT,
            message=[{"role": "user", "content": content}],
            response_model=str,
        )

        return artifact

    async def _annotate_component_artifact(
        self, artifact: ComponentSelectionArtifact
    ) -> ComponentSelectionArtifact:
        """
        Generates a description for a component selection artifact.

        :param artifact: The component selection artifact to annotate
        :return: Description string for the artifact
        """
        # Prepare component data for the prompt
        component_prompt: str = COMPONENT_USER_PROMPT.format(
            component_info=artifact.xml,
        )

        content = [{"type": "text", "text": component_prompt}]
        content.extend(artifact.image_data.openai_dict_format(0))

        artifact.description = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=COMPONENT_SYSTEM_PROMPT,
            message=[{"role": "user", "content": content}],
            response_model=str,
        )

        return artifact
