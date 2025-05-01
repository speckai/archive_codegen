"""
Utilities for extracting structured artifacts from recordings.
Transforms raw recordings into meaningful, discrete artifacts for use in contexts.
"""

import uuid

from pydantic import BaseModel, Field

from src.schemas.core.common.recordings import (
    ArtifactType,
    ComponentSelectionArtifact,
    ComponentSelectionEvent,
    ConsoleLog,
    ConsoleLogArtifact,
    EventType,
    Recording,
    RecordingArtifact,
    ReplayedEvent,
    ReplayResponse,
    ReproductionStep,
    ReproductionStepsArtifact,
    ScreenshotArtifact,
    ScrollPosition,
    VideoSegmentArtifact,
    extract_actions,
)
from src.schemas.llm import Model
from src.utils.llm.handler import chat
from src.utils.logging import logger

EXPECTED_RESULT_SYSPROMPT = """
You are a specialized analyzer that extracts expected and actual results from recording data. Your task is to understand what the user expected to happen and what actually happened.
""".strip()

EXPECTED_RESULT_PROMPT = """
I need you to analyze a recording and extract the expected and actual results.

<timeline_summary>
{timeline_summary}
</timeline_summary>

<user_actions>
{user_actions}
</user_actions>

<recording_annotation>
{recording_annotation}
</recording_annotation>

Extract the expected result (what the user thought would happen) and the actual result 
(what actually happened or went wrong) from this information.

The expected result should be derived primarily from the recording annotation or timeline summary.
The actual result should describe the error, issue, or unexpected behavior that occurred.
""".strip()


class ReproductionResults(BaseModel):
    """
    Results of analyzing a recording to extract expected and actual results.
    """

    reasoning: str = Field(description="Your reasoning for identifying these results")
    expected_result: str = Field(
        description="The expected behavior the user was anticipating"
    )
    actual_result: str = Field(description="The actual behavior or error that occurred")


async def extract_replay_artifacts(
    replay: ReplayResponse,
) -> list[RecordingArtifact]:
    """
    Main function to extract all artifacts from a replay.
    Uses the replay response for all event data.

    :param replay: The source replay (used for ID and metadata)
    :return: List of extracted RecordingArtifact objects
    """

    artifacts = []
    recording_id = replay.recording.id or f"recording_{uuid.uuid4().hex[:8]}"

    console_artifacts: list[ConsoleLogArtifact] = extract_console_artifacts(
        recording_id=recording_id,
        console_logs=replay.recording.console_logs,
        timeline=replay.replayed_events,
    )
    artifacts.extend(console_artifacts)

    repro_artifact: ReproductionStepsArtifact = (
        await create_reproduction_steps_artifact(
            recording_id=recording_id,
            timeline=replay.replayed_events,
            timeline_summary=replay.recording.annotation,
            actions=extract_actions(replay.replayed_events),
            recording=replay.recording,
        )
    )
    artifacts.append(repro_artifact)

    video_artifact_id: str = VideoSegmentArtifact.create_id(ArtifactType.VIDEO_SEGMENT)
    video_artifact: VideoSegmentArtifact = VideoSegmentArtifact(
        id=video_artifact_id,
        recording_id=recording_id,
        title=f"Full Recording: {replay.recording.name}",
        description="Recorded session showing user interaction with the application",
        timestamp=0,
        start_time=0,
        end_time=replay.recording.duration,
        video_data=replay.video_data,
    )
    artifacts.append(video_artifact)
    logger.debug(f"Added video artifact {video_artifact_id}")

    for event in replay.replayed_events:
        if event.screenshot:
            screenshot_id = ScreenshotArtifact.create_id(ArtifactType.SCREENSHOT)
            screenshot_artifact = ScreenshotArtifact(
                id=screenshot_id,
                recording_id=recording_id,
                title=f"Screenshot at {event.timestamp // 1000}s",
                description=event.annotation or None,
                timestamp=event.timestamp,
                image_data=event.screenshot,
                event_timestamp=event.timestamp,
                viewport_size=replay.recording.viewport_size,
                scroll_position=ScrollPosition(x=0, y=0),
                annotation=event.annotation,
            )
            artifacts.append(screenshot_artifact)
            logger.debug(f"Added screenshot artifact {screenshot_id}")

        if event.type == EventType.COMPONENT_SELECTION:
            component_id = ComponentSelectionArtifact.create_id(
                ArtifactType.COMPONENT_SELECTION
            )
            original_event = event.original_event
            if isinstance(original_event, ComponentSelectionEvent):
                component_artifact = ComponentSelectionArtifact(
                    id=component_id,
                    recording_id=recording_id,
                    image_data=event.screenshot,
                    title=f"Component Selection: {event.annotation or original_event.annotation or 'Unnamed'}",
                    description="User selected component in the interface",
                    timestamp=event.timestamp,
                    component=original_event.component,
                    event_timestamp=event.timestamp,
                    annotation=event.annotation or original_event.annotation,
                )
                artifacts.append(component_artifact)
                logger.debug(f"Added component selection artifact {component_id}")

    logger.debug(f"Extracted {len(artifacts)} artifacts from recording {recording_id}")
    return artifacts


def extract_console_artifacts(
    recording_id: str,
    console_logs: list[ConsoleLog],
    timeline: list[ReplayedEvent],
) -> list[ConsoleLogArtifact]:
    """
    Extracts console logs as individual artifacts.

    :param recording_id: ID of the source recording
    :param console_logs: List of console logs from the recording
    :param timeline: Processed timeline for contextual information
    :return: List of ConsoleLogArtifact objects
    """
    artifacts: list[ConsoleLogArtifact] = []

    if not console_logs:
        return artifacts

    for log in console_logs:
        if "html2canvas" in log.output:
            logger.debug(
                "Filtering out html2canvas log from paige_hook.js - needs to be removed"
            )
            continue

        context = extract_context_for_timestamp(log.timestamp, timeline)
        title = f"{log.level.value.capitalize()} at {log.timestamp / 1000:.1f}s"
        description = log.output[:100] + "..." if len(log.output) > 100 else log.output
        artifact = ConsoleLogArtifact(
            id=f"{ArtifactType.CONSOLE_LOG}_{uuid.uuid4().hex[:8]}",
            recording_id=recording_id,
            title=title,
            description=description,
            timestamp=log.timestamp,
            log=log,
            context=context,
        )
        artifacts.append(artifact)

    logger.debug(f"Created {len(artifacts)} console log artifacts")
    return artifacts


def extract_context_for_timestamp(timestamp: int, timeline: list[ReplayedEvent]) -> str:
    """
    Extracts context information for what was happening at a given timestamp.

    :param timestamp: Timestamp to get context for
    :param timeline: Processed timeline of ReplayedEvent objects
    :return: String description of the context
    """
    relevant_entries = [
        entry
        for entry in timeline
        if entry.timestamp <= timestamp and entry.timestamp >= timestamp - 5000
    ]

    if not relevant_entries:
        return "No context available"

    context_parts = []
    for entry in relevant_entries:
        if entry.type == EventType.CLICK:
            context_parts.append(f"Clicked on {entry.original_event.target.tag_name}")
        elif entry.type == EventType.INPUT:
            context_parts.append(
                f"Entered text in {entry.original_event.target.tag_name}"
            )

    if context_parts:
        return "User was: " + ", ".join(context_parts)
    return "User was interacting with the page"


async def create_reproduction_steps_artifact(
    recording_id: str,
    timeline: list[ReplayedEvent],
    timeline_summary: str,
    actions: list[str],
    recording: Recording | None = None,
) -> ReproductionStepsArtifact:
    """
    Creates a structured reproduction steps artifact from timeline.
    Uses LLM to analyze and extract expected and actual results from recording.

    :param recording_id: ID of the source recording
    :param timeline: Processed timeline of ReplayedEvent objects
    :param timeline_summary: Summary of the timeline from analysis
    :param actions: List of key actions from analysis
    :param recording: Optional Recording object for more context
    :return: ReproductionStepsArtifact
    """
    steps = []
    prev_time = 0

    for i, action in enumerate(actions):
        action_time = 0
        if i < len(timeline):
            action_time = timeline[i].timestamp

        delay = max(0, (action_time - prev_time) / 1000)

        if delay > 10:
            delay = 3

        steps.append(
            ReproductionStep(
                step=action,
                seconds_delay=delay,
            )
        )

        prev_time = action_time

    expected_result = "Expected behavior not specified"
    actual_result = "Error or unexpected behavior occurred"

    results: ReproductionResults = await chat(
        model_type=Model.GEMINI_2_0_FLASH,
        system=EXPECTED_RESULT_SYSPROMPT,
        messages=[
            {
                "role": "user",
                "content": EXPECTED_RESULT_PROMPT.format(
                    timeline_summary=timeline_summary,
                    user_actions=", ".join(actions),
                    recording_annotation=recording.annotation if recording else "",
                ),
            }
        ],
        response_model=ReproductionResults,
    )

    expected_result = results.expected_result
    actual_result = results.actual_result

    return ReproductionStepsArtifact(
        id=f"{ArtifactType.REPRODUCTION_STEPS}_{uuid.uuid4().hex[:8]}",
        recording_id=recording_id,
        title="Steps to Reproduce",
        description=timeline_summary,
        timestamp=0,
        steps=steps,
        expected_result=expected_result,
        actual_result=actual_result,
        is_reproducible=True,
    )
