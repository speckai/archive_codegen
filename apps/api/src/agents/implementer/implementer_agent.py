"""
Implementer agent that generates code based on user issues.
"""

import re

from anthropic.types.beta import (
    BetaBase64ImageSourceParam,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaTextBlockParam,
)
from src._dev.main import process_user_input
from src.agents.implementer.context import get_context
from src.agents.implementer.models import (
    AssistantMessage,
    ToolUseContext,
    ToolUseOptions,
    UserMessage,
)
from src.agents.implementer.prompts import get_system_prompt
from src.agents.implementer.tools.tools import get_all_tools
from src.agents.implementer.utils.messages import create_user_message
from src.agents.implementer.utils.persistent_shell import init_shell
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common.recordings import (
    ComponentSelectionArtifact,
    RecordingArtifact,
    ScreenshotArtifact,
    VideoSegmentArtifact,
)
from src.schemas.core.common.user_reports import BugReport


class ImplementerAgent(BaseAgent):
    """
    A simplified implementer agent that takes an issue description and generates
    XML output with file changes (update, create, delete).
    """

    def __init__(self, task):
        super().__init__(task)
        self.task = task
        self.previous_iterations: list[dict[str, str]] = []
        self.last_response: str | None = None

    async def implement_bug_report(
        self,
        bug_report: BugReport,
        debug: bool = False,
    ) -> bool:
        """
        Implement the given issue by generating XML output with file changes.

        :param bug_report: The bug report to implement
        :return: Dictionary with implementation results
        """
        await init_shell(
            self.task.sandbox,
            self.task.file_system,
            self.task.sandbox.manager.workspace_path,
            self.task,
            debug,
        )

        tool_context = ToolUseContext(
            options=ToolUseOptions(
                tools=get_all_tools(),
                max_thinking_tokens=0,
            )
        )

        # Get the context and system prompt
        context: dict[str, str] = await get_context()
        system_prompt = get_system_prompt()

        messages: list[UserMessage | AssistantMessage] = []

        label = "These are the relevant artifacts for the bug report:"
        content: list[BetaContentBlockParam] = [
            BetaTextBlockParam(text=label, type="text")
        ]
        relevant_artifacts: list[RecordingArtifact] = (
            self.task.recording_bug_report_agent.relevant_artifacts
        )
        # todo: add cache control
        for artifact in relevant_artifacts:
            if isinstance(artifact, VideoSegmentArtifact):
                continue
            content.append(BetaTextBlockParam(text=artifact.xml, type="text"))
            if isinstance(artifact, (ScreenshotArtifact, ComponentSelectionArtifact)):
                content.append(
                    BetaImageBlockParam(
                        source=BetaBase64ImageSourceParam(
                            data=artifact.image_data.data,
                            media_type=artifact.image_data.type,
                            type="base64",
                        ),
                        type="image",
                    )
                )

        messages.append(create_user_message(content))

        report = bug_report.report

        def extract_filename(url: str) -> str:
            filename = url.split("/")[-1]
            return filename.rsplit(".", 1)[0]

        report = re.sub(
            r"!\[(.*?)\]\((https://[^)]+)\)",
            lambda m: f"![{m.group(1)}]({extract_filename(m.group(2))})",
            report,
        )

        messages.append(create_user_message(report))

        await process_user_input(messages, system_prompt, context, tool_context)
        return True
