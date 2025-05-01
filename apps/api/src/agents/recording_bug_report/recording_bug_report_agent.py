"""
RecordingBugReportAgent for generating detailed bug reports from recordings.

This agent processes recordings to generate complete bug reports in a single pass
without requiring interactive back-and-forth with users.
"""

import json
import re
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from zipfile import Path

from pydantic import BaseModel
from src.agents.recorder_analyzer.recorder_analyzer_agent import RecorderAnalyzerAgent
from src.agents.recording_bug_report.utils.artifact_manager import ArtifactManager
from src.agents.recording_bug_report.utils.token_utils import TokenCounter
from src.agents.utils.base_agent import BaseAgent
from src.config import DEV
from src.schemas.core.common import (
    BugReport,
    ComponentSelectionArtifact,
    Recording,
    RecordingArtifact,
    ReplayResponse,
    ScreenshotArtifact,
    SystemInfo,
    TaskState,
    ViewportSize,
)
from src.schemas.core.common.recordings import ArtifactType
from src.schemas.core.common.types import MessageType
from src.schemas.llm import EndStream, Model, PartialStream
from src.utils.llm.calls import MAX_CLAUDE_TOKENS
from src.utils.logging import logger
from src.utils.markdown_utils import extract_title_and_content

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


BUG_REPORT_SYSTEM = """
You are a QA specialist that creates comprehensive, detailed bug reports from user recordings.
Your bug reports are precise, actionable, and follow best practices for effective QA documentation.
""".strip()

BUG_REPORT_PROMPT = """
Please analyze the previous recording of a user interaction and the related artifacts to create a detailed bug report. Code is just there for context, do not reference it in the bug report since the QA specialist reviewing the report will not understand it.

Create a comprehensive bug report that includes:

1. Title: Brief and clear identification of the feature/element and issue
   - Example: "CART - Can't add new item to cart"
   - Do not include words like "bug" or "report"
   - Make sure it uses an h1 tag
2. Description: Concise summary with searchable keywords
3. Console Logs:
   - ONLY include JavaScript errors/warnings that are directly related to the bug being reported. Ignore any other console messages, even if they indicate other issues. Do not reference them at all in the bug report if they are not related to the bug.
4. Source Path: Link to path where issue occurs (e.g. /login, /dashboard. not including the /preview/:id part that's specific to our staging environment. so /preview/1234567890/ would be /)
5. Visual Evidence:
   - Reference relevant screenshots/video clips using artifact IDs
        - Always include the video artifact in the bug report (the video_* link)
        - Always include the screenshot artifact in the bug report (the screenshot_* link)
   - Include annotations from the user
6. Steps to Reproduce:
   - Describe things in a high level logically and also include the exact steps from the recording with the replication steps artifact
7. Expected vs Actual Results:
   - Clear description of intended behavior
   - Specific details of what actually happened
8. Severity/Priority:
   - Severity: Critical/High/Medium/Low
   - Priority: High/Medium/Low
9. Environment Details:
   - Browser engine
   - Operating system
   - User agent
   - Screen resolution
   - Any other relevant technical details visible in recording
    - Ensure you do NOT hallucinate any information. If you don't know the answer, don't make up an answer. 

For any important artifacts that help explain the bug, reference them using the artifact IDs as links, using markdown image syntax. The formatting here is extremely important because our renderer will break if it's not done correctly. For example:
<example_link>
![Console error showing 405 status](console_f50196c1)
</example_link>

You shouldn't reference an artifact by its id anywhere in the bug report because that is hidden from the user. It's only there for you to use in the markdown links. Each artifact reference should be on its own line to ensure proper rendering and readability. Try to reference as many artifacts as possible for backing up anything you say in the bug report. If there are screenshots artifacts that are redundant, don't reference them. They each should be there for a reason.

Again DO NOT reference anything that is not directly related to the bug that the user is trying to solve. Your console log often has errors that are not directly related to the bug.

The user annotations are there in the artifacts, but I'm putting them all here because that what you should weight the highest with respect to what you're writing.
<user_annotations>
{user_annotations}
</user_annotations>

<system_info>
{system_info}
{viewport_size}
</system_info>

You are given a lot of information and an important part of your job is to decide what is relevant to the bug and what is not. Some logs are relevant to the bug and some are not. Same with certain screenshots, selected components, etc. Don't try to construct a report including everything, just what is directly relevant to the bug. But always include the video and a single screenshot.
""".strip()


class RecordingBugReportAgent(BaseAgent):
    """
    Agent for creating detailed bug reports from recordings.
    Processes recordings in a single pass to generate comprehensive bug reports.
    """

    def __init__(self, task: "Task"):
        """
        Initialize the RecordingBugReportAgent.

        :param task: The task object this agent belongs to
        :return: None
        """
        super().__init__(task)
        self.task = task
        self.artifact_manager = ArtifactManager(task)
        self.recorder_analyzer = RecorderAnalyzerAgent(task)
        self.replay_response: ReplayResponse | None = None
        self.bug_report: BugReport | None = None
        self.recording: Recording | None = None
        self.browser_files: list[str] = []
        self.token_counter = TokenCounter(max_tokens=200_000, tokens_per_char=4)
        self.relevant_artifacts: list[RecordingArtifact] = []

    async def generate_bug_report(
        self,
        recording: Recording,
        debug_file: Path | None = None,
    ) -> BugReport:
        """
        Main entry point for generating a bug report from a recording.
        Internally replays the recording to get multimedia content before generating the report.

        :param recording: The recording to analyze and create a bug report from
        :return: BugReport with the bug report and asset URLs
        """
        logger.debug(f"Generating bug report for recording: {recording.name}")
        await self.task.task_state_manager.send_state_update(
            TaskState.REPLAYING_RECORDING
        )
        self.recording = recording

        replay_response: ReplayResponse
        if debug_file:
            with open(debug_file, "r") as f:
                loaded_data = json.load(f)
            replay_response = ReplayResponse(**loaded_data)
        else:
            replay_response = await self._replay_recording(recording)
            self.browser_files = self.task.player.used_files
            if DEV:
                with open("temp_replay_response.json", "w") as f:
                    json.dump(replay_response.model_dump(), f)

        self.replay_response = replay_response

        self.relevant_artifacts: list[RecordingArtifact] = (
            await self.artifact_manager.process_replay_artifacts(replay_response)
        )

        await self.recorder_analyzer.keyword_search_on_console_logs(
            [
                log
                for log in self.relevant_artifacts
                if log.artifact_type == ArtifactType.CONSOLE_LOG
            ]
        )
        logger.debug(
            "TODO: do search for selected components before adding browser files"
        )

        # keyword files are added now we can add used files
        for file in self.browser_files:
            self.task.code_analyzer_agent.add_referenced_file(file)

        await self.task.task_state_manager.send_state_update(
            TaskState.GENERATING_BUG_REPORT
        )

        raw_bug_report: str = await self._generate_report(
            self.relevant_artifacts, recording.system_info, recording.viewport_size
        )

        (
            processed_report,
            asset_urls,
            text_models,
        ) = await self.task.asset_storage.store_assets(
            raw_bug_report, self.relevant_artifacts
        )

        logger.debug(
            f"Successfully generated bug report with {len(asset_urls)} multimedia assets and {len(text_models)} text assets"
        )

        title, _ = extract_title_and_content(processed_report)
        success: bool = await self.task.task_state_manager.update_task_summary(title)
        logger.debug(f"Successfully updated task summary to ({title}): {success}")

        self.bug_report = BugReport(
            report=processed_report,
            asset_urls=asset_urls,
            text_models=text_models,
        )
        return self.bug_report

    async def _replay_recording(self, recording: Recording) -> ReplayResponse:
        """
        Replay a recording to get screenshots and video data.

        :param recording: The recording to replay
        :return: ReplayResponse with video data and screenshots, or None if replay fails
        """
        logger.debug(f"Replaying recording {recording.name} to obtain visual data")

        replay_response: ReplayResponse = await self.task.player.replay_recording(
            recording, delay_multiplier=1.0
        )

        logger.debug(
            f"Successfully replayed recording with {len(replay_response.replayed_events)} events"
            + f" and {'with' if replay_response.video_data else 'without'} video data"
        )

        return replay_response

    async def _generate_report(
        self,
        relevant_artifacts: list[RecordingArtifact],
        system_info: SystemInfo,
        viewport_size: ViewportSize,
    ) -> str:
        """
        Generate the bug report using the prepared context.

        :param artifacts: List of artifacts to filter and include in the bug report
        :param system_info: System information to include in the bug report
        :param viewport_size: Viewport size information to include in the bug report
        :return: Generated bug report or None if unsuccessful
        """
        logger.debug("Generating bug report from context")

        message_content: list[dict] = []
        total_tokens: int = 0

        # Process artifacts, interleaving text and images
        for artifact in relevant_artifacts:
            # First add the artifact's XML text representation
            artifact_xml = artifact.xml
            artifact_token_count = self.token_counter.estimate_tokens(artifact_xml)

            if total_tokens + artifact_token_count > 100_000:
                message_content.append(
                    {
                        "type": "text",
                        "text": "\n<!-- Additional artifacts omitted due to token limit -->",
                    }
                )
                logger.warning(f"Omitting artifact {artifact.id} due to token limit")
                break

            # Add the artifact's text first
            message_content.append({"type": "text", "text": artifact_xml})
            total_tokens += artifact_token_count

            # Then add any associated images right after the text
            if isinstance(artifact, ScreenshotArtifact) and artifact.image_data:
                message_content.extend(
                    artifact.image_data.anthropic_dict_format(artifact.id)
                )
                total_tokens += 150
            elif (
                isinstance(artifact, ComponentSelectionArtifact) and artifact.image_data
            ):
                message_content.extend(
                    artifact.image_data.anthropic_dict_format(artifact.id)
                )
                total_tokens += 150

        # Process user annotations
        user_annotations: str = "".join(
            f"**{artifact.artifact_type} {artifact.id}**\n{artifact.annotation or ''}\n\n"
            for artifact in self.artifact_manager.relevant_artifacts
            if isinstance(artifact, (ComponentSelectionArtifact, ScreenshotArtifact))
        )

        total_tokens += (
            self.token_counter.estimate_tokens(user_annotations)
            + self.token_counter.estimate_tokens(BUG_REPORT_PROMPT)
            + self.token_counter.estimate_tokens(BUG_REPORT_SYSTEM)
        )
        remaining_tokens: int = MAX_CLAUDE_TOKENS - total_tokens

        large_context: str = await self.task.code_analyzer_agent.get_relevant_files_xml(
            remaining_tokens
        )

        # Wrap all artifacts in a single container for organization
        message_content = (
            [{"type": "text", "text": "<artifacts>"}]
            + message_content
            + [
                {"type": "text", "text": "</artifacts>"},
                {
                    "type": "text",
                    "text": f"<code_context>\n{large_context}\n</code_context>",
                },
                {
                    "type": "text",
                    "text": BUG_REPORT_PROMPT.format(
                        user_annotations=user_annotations,
                        system_info=(
                            system_info.model_dump_json() if system_info else "N/A"
                        ),
                        viewport_size=(
                            viewport_size.model_dump_json() if viewport_size else "N/A"
                        ),
                    ),
                },
            ]
        )

        logger.debug(
            f"Prepared bug report context with {total_tokens} estimated artifact tokens"
        )

        response_generator: AsyncGenerator[BaseModel, None] = await self.llm_response(
            model_type=Model.CLAUDE_SONNET,
            system=BUG_REPORT_SYSTEM,
            message=[{"role": "user", "content": message_content}],
            long_output=True,
            stream=True,
        )

        final_response: str = ""
        await self.task.ui_functions.expand_sidebar()

        async for chunk in response_generator:
            if isinstance(chunk, PartialStream):
                chunk.total_text = re.sub(
                    r"!\[(.*?)\]\((\w+)\)", r"(\1)", chunk.total_text
                )

                await self.send_update_data(
                    MessageType.BUG_REPORT_CONTENTS_PARTIAL,
                    {
                        "contents": chunk.total_text,
                    },
                )
            elif isinstance(chunk, EndStream):
                final_response = chunk.text

        return final_response
