import uuid
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
from src.schemas.core.common.files import Image, SelectedComponent


class EventType(StrEnum):
    CLICK = "click"
    SCROLL = "scroll"
    TERMINATE = "terminate"
    INPUT = "input"
    CHANGE = "change"
    SCREENSHOT = "screenshot"
    COMPONENT_SELECTION = "component_selection"
    CONSOLE_LOG = "console_log"


class RecordingType(StrEnum):
    RECORDING = "recording"


class ArtifactType(StrEnum):
    """Enum defining all artifact types for consistent identification."""

    CONSOLE_LOG = "console_log"
    REPRODUCTION_STEPS = "repro"
    VIDEO_SEGMENT = "video"
    SCREENSHOT = "screenshot"
    COMPONENT_SELECTION = "component"
    GENERIC = "artifact"  # For base or unknown types


class LogLevel(StrEnum):
    LOG = "log"
    WARN = "warn"
    ERROR = "error"
    INFO = "info"
    DEBUG = "debug"


class ScrollPosition(BaseModel):
    x: int
    y: int


class ConsoleLog(BaseModel):
    timestamp: int
    level: LogLevel
    output: str
    traceback: list[str]

    @property
    def xml(self) -> str:
        output_lines = self.output.strip().split("\n")
        primary_message = output_lines[0]
        if len(primary_message) > 150:
            primary_message = primary_message[:147] + "..."

        if len(output_lines) > 1:
            primary_message += f" (+{len(output_lines) - 1} more lines)"

        if not self.traceback:
            traceback_summary = "None"
        else:
            total_lines = len(self.traceback)

            if total_lines <= 5:
                traceback_summary = "\n".join(self.traceback)
            else:
                traceback_summary = (
                    "\n".join(self.traceback[:2])
                    + f"\n... ({total_lines - 4} frames omitted) ...\n"
                    + "\n".join(self.traceback[-2:])
                )

        return f"""
<console_log>
<level>{self.level}</level>
<output>{primary_message}</output>
<traceback_summary>({len(self.traceback)} frames){" - sample:" if self.traceback else ""}
{traceback_summary}
</traceback_summary>
</console_log>
"""


class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: float
    height: float
    center_x: float
    center_y: float

    @property
    def xml(self) -> str:
        return f"""
<bounding_box>
min_x: {self.min_x}
min_y: {self.min_y}
max_x: {self.max_x}
max_y: {self.max_y}
width: {self.width}
height: {self.height}
center_x: {self.center_x}
center_y: {self.center_y}
</bounding_box>
"""


class ViewportSize(BaseModel):
    width: int
    height: int


class EventTarget(BaseModel):
    tag_name: str
    id: str = ""
    class_name: str = ""
    name: str = ""
    value: str = ""
    checked: bool = False
    xpath: str = ""
    css_selector: str = ""
    bounding_box: BoundingBox | None = None
    inner_text: str = ""

    @property
    def xml(self) -> str:
        return f"""
<event_target>
tag_name: {self.tag_name}
id: {self.id}
class_name: {self.class_name}
name: {self.name}
value: {self.value}
checked: {self.checked}
xpath: {self.xpath}
css_selector: {self.css_selector}
inner_text: {self.inner_text}
bounding_box: {self.bounding_box.xml if self.bounding_box else "None"}
</event_target>
"""


class BaseEvent(BaseModel):
    type: EventType
    delay: int
    url: str
    target: EventTarget | None = None

    @property
    def base_xml(self) -> str:
        return f"""
<event_details>
<ms_delay>{self.delay}</ms_delay>
{self.target.xml if self.target else ""}
</event_details>
"""


class ClickEvent(BaseEvent):
    type: Literal[EventType.CLICK]
    button: int  # 0 = left click, 1 = middle click, 2 = right click

    def xml(self, idx: int) -> str:
        return f"""
<click_event index="{idx}">
button: {"left_click" if self.button == 0 else "right_click" if self.button == 2 else "middle_click"}
{self.base_xml}
</click_event>
"""


class ScrollEvent(BaseEvent):
    type: Literal[EventType.SCROLL]
    scroll_x: int
    scroll_y: int

    def xml(self, idx: int) -> str:
        return f"""
<scroll_event index="{idx}">
scroll_x: {self.scroll_x}
scroll_y: {self.scroll_y}
{self.base_xml}
</scroll_event>
"""


class TerminateEvent(BaseEvent):
    type: Literal[EventType.TERMINATE]

    def xml(self, idx: int) -> str:
        return f"""
<terminate_event index="{idx}">
action: TERMINATED RECORDING
{self.base_xml}
</terminate_event>
"""


class InputEvent(BaseEvent):
    type: Literal[EventType.INPUT]
    value: str
    checked: bool = False
    time_taken: int  # num ms

    def xml(self, idx: int) -> str:
        return f"""
<input_event index="{idx}">
value: {self.value}
checked: {self.checked}
{self.base_xml}
</input_event>
"""


class ChangeEvent(BaseEvent):
    type: Literal[EventType.CHANGE]
    value: str
    checked: bool = False

    def xml(self, idx: int) -> str:
        return f"""
<change_event index="{idx}">
value: {self.value}
checked: {self.checked}
{self.base_xml}
</change_event>
"""


class ComponentSelectionEvent(BaseEvent):
    type: Literal[EventType.COMPONENT_SELECTION]
    annotation: str
    component: SelectedComponent

    def xml(self, idx: int) -> str:
        return f"""
<component_selection_event index="{idx}">
{self.base_xml}
</component_selection_event>
"""


class ScreenshotEvent(BaseEvent):
    type: Literal[EventType.SCREENSHOT]
    annotation: str
    viewport_size: ViewportSize
    scroll_position: ScrollPosition

    def xml(self, idx: int) -> str:
        return f"""
<screenshot_event index="{idx}">
{self.base_xml}
</screenshot_event>
"""


class SystemInfo(BaseModel):
    operating_system: str
    user_agent: str


class Recording(BaseModel):
    id: str | None = None
    name: str
    annotation: str
    events: list[
        ClickEvent
        | ScrollEvent
        | TerminateEvent
        | InputEvent
        | ChangeEvent
        | ComponentSelectionEvent
        | ScreenshotEvent
    ]
    base_url: str
    initial_url: str
    duration: int
    viewport_size: ViewportSize
    console_logs: list[ConsoleLog]
    system_info: SystemInfo | None = None  # TODO: REMOVE LATER, SUPPORTS LEGACY


class ReproductionStep(BaseModel):
    step: str
    seconds_delay: float


class RecordingSummary(BaseModel):
    thinking: str
    reproduction_steps: list[ReproductionStep]
    expected_success_state: str
    current_incorrect_state: str


class RecordingCollection(BaseModel):
    recordings: list[Recording]


class ReplayedEvent(BaseModel):
    """An event that has been replayed in the browser."""

    type: EventType
    success: bool
    screenshot: Image | None = None
    annotation: str | None = None
    original_event: (
        ClickEvent
        | ScrollEvent
        | TerminateEvent
        | InputEvent
        | ChangeEvent
        | ComponentSelectionEvent
        | ScreenshotEvent
        | ConsoleLog
    ) = None
    timestamp: int | None = None  # ms since recording started


class ReplayResponse(BaseModel):
    """The response from replaying a recording."""

    success: bool
    video_data: str | None = None  # base64 encoded video data
    replayed_events: list[ReplayedEvent] = Field(default_factory=list)
    recording: Recording | None = None


class RecordingArtifact(BaseModel):
    """
    Base class for all recording-related artifacts.
    Provides common fields and functionality for derived artifact types.
    """

    id: str
    recording_id: str
    title: str
    description: str | None = None
    timestamp: int = 0  # Timestamp within recording (ms)

    @classmethod
    def create_id(cls, artifact_type: ArtifactType = ArtifactType.GENERIC) -> str:
        """
        Create a standardized ID for this artifact type.

        :param artifact_type: The type of artifact
        :return: A standardized ID with prefix corresponding to the artifact type
        """

        return f"{artifact_type.value}_{uuid.uuid4().hex[:8]}"

    @property
    def artifact_type(self) -> ArtifactType:
        """
        Get the type of this artifact.
        Base implementation returns GENERIC.

        :return: The ArtifactType of this artifact
        """
        return ArtifactType.GENERIC

    @property
    def xml(self) -> str:
        """
        Base implementation that derived classes should override.

        :return: XML string representation of the artifact
        """
        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<description>{self.description or ""}</description>
<timestamp>{self.timestamp}</timestamp>
</recording_artifact>
""".strip()


class ConsoleLogArtifact(RecordingArtifact):
    """
    Represents an individual console log entry with context.
    Allows for flexible placement of console logs within bug reports.
    """

    log: ConsoleLog
    context: str | None = None

    @property
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.CONSOLE_LOG

    @property
    def xml(self) -> str:
        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<timestamp>{self.timestamp}</timestamp>
<context>{self.context or ""}</context>
<log>
{self.log.xml}
</log>
</recording_artifact>
"""


class ReproductionStepsArtifact(RecordingArtifact):
    """
    Structured representation of steps to reproduce an issue.
    Derived from recording timeline with analysis.
    """

    steps: list[ReproductionStep]
    expected_result: str
    actual_result: str
    is_reproducible: bool = True

    @property
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.REPRODUCTION_STEPS

    @property
    def xml(self) -> str:
        steps_xml = "\n".join(
            f"""
<step>
<description>{step.step}</description>
<delay>{step.seconds_delay}</delay>
</step>
            """.strip()
            for step in self.steps
        )

        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<description>{self.description or ""}</description>
<timestamp>{self.timestamp}</timestamp>
<expected_result>{self.expected_result}</expected_result>
<actual_result>{self.actual_result}</actual_result>
<is_reproducible>{str(self.is_reproducible).lower()}</is_reproducible>
<steps>
{steps_xml}
</steps>
</recording_artifact>
""".strip()


class VideoSegmentArtifact(RecordingArtifact):
    """
    Video segment from a recording that demonstrates a specific issue or behavior.
    Designed to be placed at relevant points in a bug report.
    """

    start_time: int  # ms from start of recording
    end_time: int  # ms from start of recording
    video_data: str | None = None  # base64 encoded video data

    @property
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.VIDEO_SEGMENT

    @property
    def xml(self) -> str:
        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<description>{self.description or ""}</description>
<timestamp>{self.timestamp}</timestamp>
<start_time>{self.start_time}</start_time>
<end_time>{self.end_time}</end_time>
<has_video_data>{bool(self.video_data)}</has_video_data>
</recording_artifact>
"""


class ScreenshotArtifact(RecordingArtifact):
    """
    Screenshot artifact from a recording.
    Captures a specific moment in the recording with image data and context.
    """

    image_data: Image  # Base64 encoded image data
    event_timestamp: int
    viewport_size: ViewportSize
    scroll_position: ScrollPosition
    annotation: str | None = None

    @property
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.SCREENSHOT

    @property
    def xml(self) -> str:
        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<description>{self.description or ""}</description>
<timestamp>{self.timestamp}</timestamp>
<event_timestamp>{self.event_timestamp}</event_timestamp>
<annotation>{self.annotation or ""}</annotation>
<viewport_width>{self.viewport_size.width}</viewport_width>
<viewport_height>{self.viewport_size.height}</viewport_height>
<scroll_x>{self.scroll_position.x}</scroll_x>
<scroll_y>{self.scroll_position.y}</scroll_y>
</recording_artifact>
"""


class ComponentSelectionArtifact(RecordingArtifact):
    """
    Component selection artifact from a recording.
    Captures a user-selected component with associated metadata and context.
    """

    component: SelectedComponent
    event_timestamp: int
    annotation: str | None = None
    bounding_box: BoundingBox | None = None
    image_data: Image | None = None

    @property
    def artifact_type(self) -> ArtifactType:
        return ArtifactType.COMPONENT_SELECTION

    @property
    def xml(self) -> str:
        component_xml = ""

        # Include component details if available
        if not self.component.no_component_info:
            component_xml = f"""
<component_name>{self.component.component_name or ""}</component_name>
<file_path>{self.component.file_path or ""}</file_path>
<line_number>{self.component.line_number if self.component.line_number is not None else ""}</line_number>
""".strip()
        else:
            component_xml = f"""
<html_tag>{self.component.html_tag or ""}</html_tag>
<html_class_name>{self.component.html_class_name or ""}</html_class_name>
<html_children>{self.component.html_children or ""}</html_children>
""".strip()

        # Include bounding box if available
        bounding_box_xml = ""
        if self.bounding_box:
            bounding_box_xml = f"""
<bounding_box>
<min_x>{self.bounding_box.min_x}</min_x>
<min_y>{self.bounding_box.min_y}</min_y>
<max_x>{self.bounding_box.max_x}</max_x>
<max_y>{self.bounding_box.max_y}</max_y>
<width>{self.bounding_box.width}</width>
<height>{self.bounding_box.height}</height>
</bounding_box>
""".strip()

        return f"""
<recording_artifact type="{self.artifact_type.value}">
<id>{self.id}</id>
<title>{self.title}</title>
<description>{self.description or ""}</description>
<timestamp>{self.timestamp}</timestamp>
<event_timestamp>{self.event_timestamp}</event_timestamp>
<annotation>{self.annotation or ""}</annotation>{component_xml}{bounding_box_xml}
<has_screenshot>{bool(self.image_data)}</has_screenshot>
</recording_artifact>
""".strip()


def extract_actions(
    timeline: list[ReplayedEvent],
) -> list[str]:
    """
    Extract user actions and errors from the timeline using pattern matching.

    :param timeline: List of ReplayedEvent objects
    :return: List of user actions and errors
    """
    actions = []

    for entry in timeline:
        if entry.type == EventType.CLICK:
            target = entry.original_event.target
            action = f"Clicked on {target.tag_name}"
            if target.inner_text:
                action += f" with text '{target.inner_text}'"
            actions.append(action)

        elif entry.type == EventType.INPUT:
            target = entry.original_event.target
            value = getattr(entry.original_event, "value", "")
            action = f"Entered text in {target.tag_name}"
            if value:
                action += f": '{value}'"
            actions.append(action)

        elif entry.type == EventType.CHANGE:
            target = entry.original_event.target
            value = getattr(entry.original_event, "value", "")
            action = f"Changed value in {target.tag_name}"
            if value:
                action += f" to '{value}'"
            actions.append(action)

        elif (
            entry.type == EventType.CONSOLE_LOG
            and entry.original_event
            and entry.original_event.level == "ERROR"
        ):
            actions.append(entry.original_event.output)

        elif entry.type == EventType.COMPONENT_SELECTION:
            action = f"Selected component with annotation: '{entry.annotation}'"
            actions.append(action)

        elif entry.type == EventType.SCREENSHOT:
            action = f"Took screenshot with annotation: '{entry.annotation}'"
            actions.append(action)

    return actions
