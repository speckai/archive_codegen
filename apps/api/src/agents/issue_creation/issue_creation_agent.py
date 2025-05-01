"""
Issue Creation Agent for generating detailed issue descriptions from bug reports.
"""

from typing import TYPE_CHECKING

from src.agents.issue_creation.prompts import (
    ISSUE_CREATION_PROMPT,
    ISSUE_CREATION_SYSPROMPT,
)
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common import BugReport, IssueContents
from src.schemas.core.common.recordings import (
    ComponentSelectionArtifact,
    RecordingArtifact,
    ScreenshotArtifact,
)
from src.schemas.llm import Model
from src.utils.llm.calls import MAX_CLAUDE_TOKENS
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class IssueCreationAgent(BaseAgent):
    """
    Agent for creating detailed issue descriptions from bug reports.
    Performs deep research, gathers context, and validates the quality of the issue description.
    """

    def __init__(self, task: "Task"):
        super().__init__(task)
        self.task = task
        self.issue_description: str | None = None

    async def generate_issue_description(self, bug_report: BugReport) -> IssueContents:
        """
        Generate the issue description using a bug report.

        :param bug_report: BugReport containing the bug report
        :return: IssueContents with description and assets
        """
        logger.debug("Generating issue description from bug report")

        message_content: list[dict] = []
        total_tokens: int = 0

        artifacts: list[RecordingArtifact] = (
            self.task.recording_bug_report_agent.artifact_manager.relevant_artifacts
        )

        # Process artifacts, interleaving text and images
        for artifact in artifacts:
            # First add the artifact's XML text representation
            artifact_xml = artifact.xml
            artifact_token_count = (
                self.task.recording_bug_report_agent.token_counter.estimate_tokens(
                    artifact_xml
                )
            )

            if total_tokens + artifact_token_count > 100000:
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

        # Add token counts for prompts
        total_tokens += (
            self.task.recording_bug_report_agent.token_counter.estimate_tokens(
                ISSUE_CREATION_PROMPT
            )
            + self.task.recording_bug_report_agent.token_counter.estimate_tokens(
                ISSUE_CREATION_SYSPROMPT
            )
        )
        remaining_tokens: int = MAX_CLAUDE_TOKENS - total_tokens

        large_context: str = await self.task.code_analyzer_agent.get_relevant_files_xml(
            remaining_tokens
        )

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
                    "text": ISSUE_CREATION_PROMPT.format(
                        bug_report_text=bug_report.report,
                    ),
                },
            ]
        )

        logger.debug(
            f"Prepared issue creation context with {total_tokens} estimated tokens"
        )

        raw_issue_description: str = await self.llm_response(
            model_type=Model.CLAUDE_SONNET,
            system=ISSUE_CREATION_SYSPROMPT,
            message=[{"role": "user", "content": message_content}],
            long_output=True,
        )

        artifacts: list[RecordingArtifact] = (
            self.task.recording_bug_report_agent.artifact_manager.relevant_artifacts
        )

        (
            content,
            asset_urls,
            text_models,
        ) = await self.task.asset_storage.store_assets(raw_issue_description, artifacts)

        return IssueContents(
            content=content,
            asset_urls=asset_urls,
            text_models=text_models,
        )
