import asyncio
import time
from typing import TYPE_CHECKING

from src.agents.code_analyzer.code_analyzer_agent import CodeAnalyzerAgent
from src.agents.implementer.implementer_agent import ImplementerAgent
from src.agents.issue_creation.issue_creation_agent import IssueCreationAgent
from src.agents.recording_bug_report.recording_bug_report_agent import (
    RecordingBugReportAgent,
)
from src.agents.utils.task.interfaces.browsing.recorder_player import RecordingPlayer
from src.agents.validation.validation_agent import ValidationAgent
from src.agents.validation.visual.visual_tester import VisualTester
from src.schemas.core.common import (
    MessageType,
    SerializedTask,
)
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Initializer:
    def __init__(self, task: "Task"):
        self.task = task
        self._initialize_task: asyncio.Task | None = None

    async def initialize(self):
        self._initialize_task = asyncio.current_task()
        try:
            self.task.validation_agent = ValidationAgent(self.task)
            self.task.code_analyzer_agent = CodeAnalyzerAgent(self.task)
            self.task.implementer_agent = ImplementerAgent(self.task)
            self.task.issue_creation_agent = IssueCreationAgent(self.task)
            saved_task: SerializedTask | None = (
                self.task.task_state_manager.get_saved_task()
            )
            self.task.recording_bug_report_agent = RecordingBugReportAgent(self.task)
            self.task.visual_tester = VisualTester(self.task, None)
            self.task.player = RecordingPlayer(self.task)

            await self.task.send_update_data(MessageType.ALLOCATING, {})
            start_time: float = time.time()
            preview_url: str = await self.task.sandbox.initialize_sandbox()
            logger.info(
                f"Sandbox initialized in {time.time() - start_time:.2f} seconds at {preview_url}"
            )
            await self.task.task_state_manager.send_task_details()

            if self.task.debug and self.task.debug.initial_commit:
                await self.task.sandbox.run_command(
                    f"cd /repo && git checkout {self.task.debug.initial_commit}",
                )
            if saved_task:
                await self.task.task_state_manager.load_saved_task_files(saved_task)

            # dependencies, dev_dependencies = await self.file_system.get_dependencies()
            # print(dependencies, dev_dependencies)

            if saved_task is not None:
                await self.task.task_state_manager.load_saved_task_actions(saved_task)

            await asyncio.sleep(0.25)
            await self.task.send_update_data(
                MessageType.SET_PREVIEW_URL, {"url": preview_url}
            )
            await self.task.send_update_data(MessageType.INITIALIZATION_SUCCESS, {})

            # Index codebase in the background
            # asyncio.create_task(self.task.search_agent.index_codebase())

        except asyncio.CancelledError:
            logger.info("Initialization was cancelled")
            raise
        finally:
            self._initialize_task = None

    def cancel(self):
        if self._initialize_task is not None:
            self._initialize_task.cancel()
