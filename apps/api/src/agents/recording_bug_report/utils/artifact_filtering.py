"""
Artifact filtering module for the recording bug report agent.
Provides functions to filter and prioritize artifacts for bug reports.
"""

from typing import TypeVar, cast

from pydantic import BaseModel, Field
from src.schemas.core.common.recordings import (
    ArtifactType,
    ComponentSelectionArtifact,
    ConsoleLogArtifact,
    RecordingArtifact,
    ReplayResponse,
    ScreenshotArtifact,
)
from src.utils.llm.handler import Model, chat
from src.utils.logging import logger

T = TypeVar("T", bound=RecordingArtifact)


class ConsoleLogFilterResponse(BaseModel):
    """Structured response for console log filtering."""

    thinking: str = Field(
        ...,
        description="Detailed chain of thought reasoning about the annotations, logs, and their relationships",
    )
    relevant_log_ids: list[str] = Field(
        ...,
        description=f"List of log IDs that should be kept in the final report. Of the format {ArtifactType.CONSOLE_LOG.value}_<uuid>",
    )


class ScreenshotFilterResponse(BaseModel):
    """Structured response for screenshot filtering."""

    thinking: str = Field(
        ...,
        description="Detailed chain of thought reasoning about the annotations, screenshots, and their relationships",
    )
    relevant_screenshot_ids: list[str] = Field(
        ...,
        description=f"List of screenshot IDs that should be kept in the final report. Of the format {ArtifactType.SCREENSHOT.value}_<uuid>",
    )


class ComponentSelectionFilterResponse(BaseModel):
    """Structured response for component selection filtering."""

    thinking: str = Field(
        ...,
        description="Detailed chain of thought reasoning about the annotations, component selections, and their relationships",
    )
    relevant_component_ids: list[str] = Field(
        ...,
        description=f"List of component selection IDs that should be kept in the final report. Of the format {ArtifactType.COMPONENT_SELECTION.value}_<uuid>",
    )


async def filter_artifacts(
    artifacts: list[RecordingArtifact], replay: ReplayResponse
) -> list[RecordingArtifact]:
    """
    Main entry point for artifact filtering.
    Filters and prioritizes artifacts for inclusion in bug reports.

    :param artifacts: Complete list of all extracted artifacts
    :param replay: The replay response containing annotations and events
    :return: Filtered list of relevant artifacts for the bug report
    """
    if not artifacts:
        logger.warning("No artifacts provided for filtering")
        return []

    annotations = [
        f"<type>{a.type}</type>\n<annotation>{a.annotation}</annotation>\n<timestamp>{a.timestamp}</timestamp>"
        for a in replay.replayed_events
        if a.annotation
    ]
    logger.debug(f"Filtering {len(artifacts)} artifacts")

    # Filter by artifact type
    console_logs = [a for a in artifacts if a.artifact_type == ArtifactType.CONSOLE_LOG]
    screenshots = [a for a in artifacts if a.artifact_type == ArtifactType.SCREENSHOT]
    component_selections = [
        a for a in artifacts if a.artifact_type == ArtifactType.COMPONENT_SELECTION
    ]
    video_segments = [
        a for a in artifacts if a.artifact_type == ArtifactType.VIDEO_SEGMENT
    ]
    repro_steps = [
        a for a in artifacts if a.artifact_type == ArtifactType.REPRODUCTION_STEPS
    ]

    filtered_console_logs = await _filter_console_logs(
        cast(list[ConsoleLogArtifact], console_logs), annotations
    )
    filtered_screenshots = await _filter_screenshots(
        cast(list[ScreenshotArtifact], screenshots), annotations
    )
    filtered_components = await _filter_component_selections(
        cast(list[ComponentSelectionArtifact], component_selections), annotations
    )

    filtered_artifacts: list[RecordingArtifact] = (
        filtered_console_logs
        + filtered_screenshots
        + filtered_components
        + video_segments
        + repro_steps
    )

    logger.debug(
        f"Filtered artifacts from {len(artifacts)} to {len(filtered_artifacts)} relevant items"
    )
    return filtered_artifacts


async def _filter_console_logs(
    artifacts: list[ConsoleLogArtifact],
    annotations: list[str],
) -> list[ConsoleLogArtifact]:
    """
    Filter console logs based on their relevance to annotations and the reported bug.

    :param artifacts: List of console log artifacts to filter
    :param annotations: List of annotation information from the replay
    :return: Filtered list of console log artifacts
    """
    # Format console logs for the prompt
    logs_text = [log.xml for log in artifacts]
    # Create the prompt
    prompt = f"""
You're analyzing a list of artifacts from a user session recording to identify which ones are relevant to the user's bug report. You're only given some annotations that the user made at certain points in the recording, and you'll have to infer which ones are out of context or not relevant to the bug report. Even if they are problems, you'll only keep the ones that are relveant to look at to fix the bug the user is currently facing.

# Reported Annotations
{"\n".join(annotations)}

# Artifacts
Below are all artifacts captured during the recording:

{"\n".join(logs_text)}

# Task
Analyze the artifacts and determine which ones are relevant to the issues described in the annotations.
Focus on:
1. Errors and warnings that correlate with the timing or nature of reported issues
2. Logs that provide context about the application state during the reported issues
3. Logs that might indicate the root cause of the reported issues

Consider:
- Relevance to the bug report
- Uniqueness (avoid duplicate information)

Provide a structured response indicating which logs should be kept and why.""".strip()

    response: ConsoleLogFilterResponse = await chat(
        model_type=Model.GEMINI_2_0_FLASH,
        system="You are a console log analyzer that identifies logs relevant to reported bugs.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        response_model=ConsoleLogFilterResponse,
    )

    logs_to_keep = [log for log in artifacts if log.id in response.relevant_log_ids]
    logger.debug(f"Filtered console logs from {len(artifacts)} to {len(logs_to_keep)}")
    logger.debug(f"Filtering summary: {response.thinking}")

    return logs_to_keep


async def _filter_screenshots(
    artifacts: list[ScreenshotArtifact],
    annotations: list[str],
) -> list[ScreenshotArtifact]:
    """
    Filter screenshots to include only those relevant to the bug report.

    Filtering criteria:
    - Select key moments in the interaction
    - Remove visually similar screenshots
    - Prioritize screenshots with user annotations

    :param artifacts: List of screenshot artifacts
    :param annotations: List of annotation information from the replay
    :return: Filtered list of screenshot artifacts
    """
    if not artifacts:
        return []

    screenshots_text = [screenshot.xml for screenshot in artifacts]
    # Create the prompt
    prompt = f"""
You're analyzing a list of screenshots from a user session recording to identify which ones are relevant to the user's bug report. You're only given some annotations that the user made at certain points in the recording, and you'll have to determine which screenshots are most meaningful for understanding the reported bug.

# Reported Annotations
{"\n".join(annotations)}

# Task
Analyze the screenshots and determine which ones are most relevant to the issues described in the annotations.
Focus on:
1. Screenshots that show the actual bug or error state
2. Screenshots that provide context about the application state before/after the issue
3. Screenshots that correspond with key moments mentioned in annotations
4. Screenshots with user annotations about the issue

Consider:
- Relevance to the bug report
- Uniqueness (avoid nearly identical screenshots)
- Visual evidence of the reported problem

Provide a structured response indicating which screenshots should be kept and why.Each artifact will be below with their metadata and image.""".strip()

    images = []
    for screenshot in artifacts:
        images.extend(screenshot.image_data.openai_dict_format(screenshot.xml))
    response: ScreenshotFilterResponse = await chat(
        model_type=Model.GEMINI_2_0_FLASH,
        system="You are a screenshot analyzer that identifies images relevant to reported bugs.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    *images,
                ],
            }
        ],
        response_model=ScreenshotFilterResponse,
    )

    # Use the structured response to filter screenshots
    screenshots_to_keep = [
        screenshot
        for screenshot in artifacts
        if screenshot.id in response.relevant_screenshot_ids
    ]
    logger.debug(
        f"Filtered screenshots from {len(artifacts)} to {len(screenshots_to_keep)}"
    )
    logger.debug(f"Screenshot filtering summary: {response.thinking}")

    return screenshots_to_keep


async def _filter_component_selections(
    artifacts: list[ComponentSelectionArtifact],
    annotations: list[str],
) -> list[ComponentSelectionArtifact]:
    """
    Filter component selections to include only those relevant to the bug report.

    Filtering criteria:
    - Focus on components with user annotations
    - Remove duplicates of the same component
    - Prioritize by relevance to the bug

    :param artifacts: List of component selection artifacts
    :param annotations: List of annotation information from the replay
    :return: Filtered list of component selection artifacts
    """
    if not artifacts:
        return []

    # Format component selections for the prompt
    components_text = []
    for component in artifacts:
        components_text.append(component.xml)

    # Create the prompt
    prompt = f"""
You're analyzing a list of UI component selections from a user session recording to identify which ones are relevant to the user's bug report. You're only given some annotations that the user made at certain points in the recording, and you'll have to determine which component selections are most meaningful for understanding the reported bug.

# Reported Annotations
{"\n".join(annotations)}

# Task
Analyze the component selections and determine which ones are most relevant to the issues described in the annotations.
Focus on:
1. Components directly related to the reported bug (e.g., a button that doesn't work)
2. Components that provide context about where the issue occurs
3. Components with user annotations about the issue
4. Components that represent key UI elements involved in the bug

Consider:
- Relevance to the bug report
- Uniqueness (avoid duplicate selections of the same component)
- Components that help identify problematic parts of the interface

Provide a structured response indicating which component selections should be kept and why.Each artifact will be below with their metadata and image.""".strip()

    images = [
        component.image_data.openai_dict_format(component.xml)
        for component in artifacts
    ]
    response: ComponentSelectionFilterResponse = await chat(
        model_type=Model.GEMINI_2_0_FLASH,
        system="You are a UI component analyzer that identifies elements relevant to reported bugs.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    *images,
                ],
            }
        ],
        response_model=ComponentSelectionFilterResponse,
    )

    # Use the structured response to filter component selections
    components_to_keep = [
        component
        for component in artifacts
        if component.id in response.relevant_component_ids
    ]
    logger.debug(
        f"Filtered component selections from {len(artifacts)} to {len(components_to_keep)}"
    )
    logger.debug(f"Component selection filtering summary: {response.thinking}")

    return components_to_keep
