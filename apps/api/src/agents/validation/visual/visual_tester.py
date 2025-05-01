from typing import TYPE_CHECKING

from src.agents.recording_bug_report.utils.formatting import enrich_bug_report
from src.agents.utils.base_agent import BaseAgent
from src.agents.utils.task.interfaces.browsing.recorder_player import RecordingPlayer
from src.prompts.validation import VALIDATION_SYSTEM, VALIDATION_USER_PROMPT
from src.schemas.core.common.recordings import (
    EventType,
    ReplayedEvent,
    ReplayResponse,
)
from src.schemas.core.validation.visual import (
    LLMValidationResponse,
    VisualValidationEvent,
    VisualValidationResponse,
)
from src.utils.llm.handler import Model, chat
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task
    from src.agents.validation.validation_agent import ValidationAgent


class VisualTester(BaseAgent):
    def __init__(
        self,
        task: "Task",
        agent: "ValidationAgent",
    ):
        super().__init__(task)
        self.task = task
        self.agent = agent

    async def validate_functionality(self) -> VisualValidationResponse:
        validation_events: list[VisualValidationEvent] = []
        player = RecordingPlayer(self.task)
        previous_replay: ReplayResponse = (
            self.task.recording_bug_report_agent.replay_response
        )
        new_replay: ReplayResponse = await player.replay_recording(
            self.task.recording_bug_report_agent.recording
        )

        for previous_replay_event, new_replay_event in zip(
            previous_replay.replayed_events, new_replay.replayed_events
        ):
            if previous_replay_event.type in [
                EventType.SCREENSHOT,
                EventType.COMPONENT_SELECTION,
            ]:
                if not previous_replay_event.screenshot:
                    logger.error(
                        f"No screenshot for {previous_replay_event.type} event"
                    )
                    continue

                validation_event: VisualValidationEvent = await self._validate_event(
                    previous_replay_event, new_replay_event
                )
                logger.info(
                    f"annotation: {previous_replay_event.annotation}\n"
                    f"success: {validation_event.success}\n"
                    f"rationale: {validation_event.rationale}"
                )
                validation_events.append(validation_event)

        return VisualValidationResponse(
            overall_success=all(event.success for event in validation_events),
            events=validation_events,
        )

    async def _validate_event(
        self, previous_replay_event: ReplayedEvent, new_replay_event: ReplayedEvent
    ) -> VisualValidationEvent:
        logger.info(f"Validating {previous_replay_event.type} event")
        filled_bug_report: str = enrich_bug_report(
            self.task.recording_bug_report_agent.bug_report
        )
        logger.info(f"Length of filled bug report: {len(filled_bug_report)}")
        response: LLMValidationResponse = await chat(
            model_type=Model.GEMINI_2_0_FLASH,
            system=VALIDATION_SYSTEM(),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VALIDATION_USER_PROMPT(
                                previous_replay_event.annotation, filled_bug_report
                            ),
                        },
                        *previous_replay_event.screenshot.openai_dict_format(
                            "Before the fix"
                        ),
                        *new_replay_event.screenshot.openai_dict_format(
                            "After the fix"
                        ),
                    ],
                }
            ],
            response_model=LLMValidationResponse,
        )
        logger.info(
            f"Prompt: {VALIDATION_USER_PROMPT(previous_replay_event.annotation, filled_bug_report)}"
        )

        return VisualValidationEvent(
            event_type=previous_replay_event.type,
            before_screenshot=previous_replay_event.screenshot,
            after_screenshot=new_replay_event.screenshot,
            annotation=previous_replay_event.annotation,
            success=response.success,
            rationale=response.rationale,
        )
