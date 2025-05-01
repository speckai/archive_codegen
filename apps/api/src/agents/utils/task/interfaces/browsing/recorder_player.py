import asyncio
import base64
import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import ElementHandle
from src.agents.utils.gitignore_utils import filter_ignored_files
from src.agents.utils.task.interfaces.browsing.test_browser import TestBrowser
from src.config import DEV
from src.prompts.recording import (
    SUMMARIZE_RECORDING_SYSTEM_PROMPT,
    SUMMARIZE_RECORDING_USER_PROMPT,
)
from src.schemas.core.common.files import Image
from src.schemas.core.common.recordings import (
    ChangeEvent,
    ClickEvent,
    ComponentSelectionEvent,
    EventTarget,
    EventType,
    InputEvent,
    Recording,
    RecordingCollection,
    RecordingSummary,
    ReplayedEvent,
    ReplayResponse,
    ScreenshotEvent,
    ScrollEvent,
    TerminateEvent,
)
from src.schemas.core.common.types import MessageType
from src.schemas.llm import Model
from src.utils.llm.handler import chat
from src.utils.logging import logger

SAVE_TO_DISK: bool = DEV


if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class RecordingPlayer:
    """
    A class to replay recordings captured from the browser recorder.
    Translates recorded events into Playwright actions that can be executed by TestBrowser.
    """

    def __init__(self, task: "Task" = None):
        self.browser: "TestBrowser" = None
        self.task = task
        self.replayed_events: list[ReplayedEvent] = []
        self.used_files: list[str] = []

    async def replay_recording(
        self,
        recording: "Recording",
        delay_multiplier: float = 1.0,
    ) -> ReplayResponse:
        """
        Replays a single recording.
        Creates and launches a browser with the correct viewport size.

        :param recording: The Recording to replay
        :param delay_multiplier: Factor to adjust delays between actions (1.0 = original timing)
        :return: A ReplayResponse containing the video data and screenshots
        """
        browser_start_time: datetime.datetime = await self._setup_browser(recording)

        trim_duration_seconds: float = await self._navigate_to_initial_state(
            recording, browser_start_time
        )

        await self._replay_all_events(recording, delay_multiplier)

        logger.info("Getting used files")
        used_files: list[str] = await self.browser.get_used_files()
        logger.info(f"len(used_files): {len(used_files)}")
        used_files = await filter_ignored_files(self.task, used_files)
        if DEV:
            with open("temp_used_files.json", "w") as f:
                json.dump(used_files, f)
        logger.info(f"Actual used files: {used_files}")
        self.used_files.extend(used_files)

        await self.browser.stop_recording()

        video_data: bytes | None = await self._get_video_data(trim_duration_seconds)

        if SAVE_TO_DISK:
            await self._save_data_to_disk(video_data)

        await self.browser.stop()

        for console_log in recording.console_logs:
            self.replayed_events.append(
                ReplayedEvent(
                    type=EventType.CONSOLE_LOG,
                    success=True,
                    original_event=console_log,
                    timestamp=int(console_log.timestamp),
                )
            )
        self.replayed_events.sort(key=lambda x: x.timestamp)
        video_data_str: str | None = (
            base64.b64encode(video_data).decode() if video_data else None
        )
        logger.debug(f"Video data str: {video_data_str[:10]}")
        if DEV:
            with open("temp_replay_response.json", "w") as f:
                json.dump(
                    ReplayResponse(
                        success=True,
                        video_data=video_data_str,
                        replayed_events=self.replayed_events,
                        recording=recording,
                    ).model_dump(),
                    f,
                )
        return ReplayResponse(
            success=True,
            video_data=video_data_str,
            replayed_events=self.replayed_events,
            recording=recording,
        )

    async def _setup_browser(self, recording: "Recording") -> datetime.datetime:
        """
        Sets up the browser with the correct viewport size.

        :param recording: The Recording to replay
        :return: The browser start time
        """
        resolution: tuple[int, int] = (
            recording.viewport_size.width,
            recording.viewport_size.height,
        )

        self.browser = TestBrowser(self.task, resolution, base_url=recording.base_url)
        await self.browser.start()
        browser_start_time: datetime.datetime = datetime.datetime.now()

        if self.browser.page:
            await self._clear_previous_highlight()

        return browser_start_time

    async def _navigate_to_initial_state(
        self, recording: "Recording", browser_start_time: datetime.datetime
    ) -> float:
        """
        Navigates to the initial URL and sets the initial scroll position.

        :param recording: The Recording to replay
        :param browser_start_time: The time when the browser was started
        :return: The duration in seconds to trim from the start of the video
        """
        logger.info(f"Navigating to initial URL: {recording.initial_url}")
        await self.browser.navigate_to_url(recording.initial_url)

        await asyncio.sleep(3)

        trim_point_time: datetime.datetime = datetime.datetime.now()
        trim_duration_seconds: float = (
            trim_point_time - browser_start_time
        ).total_seconds()
        logger.info(
            f"Video will be trimmed at {trim_duration_seconds:.2f} seconds from the start"
        )

        await asyncio.sleep(1)
        return trim_duration_seconds

    async def _replay_all_events(
        self, recording: "Recording", delay_multiplier: float = 1.0
    ) -> bool:
        """
        Replays all events in the recording.

        :param recording: The Recording to replay
        :param delay_multiplier: Factor to adjust delays between actions
        :return: Whether the replay was successful
        """
        last_event_time: float = datetime.datetime.now().timestamp()

        for i, event in enumerate(recording.events):
            logger.info(f"Replaying event {i + 1}/{len(recording.events)}")
            await self.task.send_update_data(
                MessageType.RECORDER_PROGRESS,
                {
                    "index": i + 1,
                    "total": len(recording.events),
                    "type": event.type,
                },
            )

            last_event_time = await self._handle_event_timing(
                event, last_event_time, delay_multiplier
            )

            try:
                await self._replay_event(event, i)
            except Exception as e:
                logger.error(f"Error replaying event {i}: {e}")
                continue

        return True

    async def _handle_event_timing(
        self,
        event: ClickEvent | ScrollEvent | TerminateEvent | InputEvent | ChangeEvent,
        last_event_time: float,
        delay_multiplier: float,
    ) -> float:
        """
        Handles the timing between events based on the recorded delay.

        :param event: The event to replay
        :param last_event_time: The timestamp of the last event
        :param delay_multiplier: Factor to adjust delays between actions
        :return: The new last event time
        """
        current_time: float = datetime.datetime.now().timestamp()
        time_elapsed: float = (current_time - last_event_time) * 1000

        delay_to_wait: float = max(0, (event.delay * delay_multiplier) - time_elapsed)

        if delay_to_wait > 0:
            logger.info(f"Waiting {delay_to_wait:.2f}ms before next action")
            await asyncio.sleep(delay_to_wait / 1000)

        return datetime.datetime.now().timestamp()

    async def _replay_event(
        self,
        event: ClickEvent
        | ScrollEvent
        | TerminateEvent
        | InputEvent
        | ChangeEvent
        | ComponentSelectionEvent
        | ScreenshotEvent,
        event_index: int,
    ) -> None:
        """Replays a single event based on its type."""
        await self._clear_previous_highlight()

        if self.browser.page.url != event.url:
            logger.info(f"URL changed, navigating to: {event.url}")
            await self.browser.navigate_to_url(event.url)

        try:
            success: bool = True
            screenshot: Image | None = None

            if event.type == EventType.CLICK:
                success = await self._replay_click_event(event, event_index)
                screenshot = await self._capture_screenshot(event_index)
            elif event.type == EventType.SCROLL:
                success = await self._replay_scroll_event(event)
                screenshot = await self._capture_screenshot(event_index)
            elif event.type == EventType.INPUT:
                success = await self._replay_input_event(event, event_index)
                screenshot = await self._capture_screenshot(event_index)
            elif event.type == EventType.CHANGE:
                success = await self._replay_change_event(event, event_index)
                screenshot = await self._capture_screenshot(event_index)
            elif event.type == EventType.TERMINATE:
                screenshot = await self._capture_screenshot(event_index)
            elif event.type == EventType.SCREENSHOT:
                success, screenshot = await self._replay_screenshot_event(
                    event, event_index
                )
            elif event.type == EventType.COMPONENT_SELECTION:
                success, screenshot = await self._replay_component_selection_event(
                    event, event_index
                )
            else:
                logger.warning(f"Unknown event type: {event.type}")
                success = False

            self.replayed_events.append(
                ReplayedEvent(
                    type=event.type,
                    success=success,
                    screenshot=screenshot,
                    annotation=getattr(event, "annotation", None),
                    original_event=event,
                    timestamp=int(datetime.datetime.now().timestamp() * 1000),
                )
            )
        except Exception as e:
            logger.error(f"Error replaying event {event.type}: {e}")
            self.replayed_events.append(
                ReplayedEvent(
                    type=event.type,
                    success=False,
                    screenshot=None,
                    original_event=event,
                    timestamp=int(datetime.datetime.now().timestamp() * 1000),
                )
            )

    async def _replay_click_event(self, event: ClickEvent, event_index: int) -> bool:
        """
        Replays a click event using the element handle from _get_element_from_target.
        """
        target = event.target
        if not target:
            logger.error("Click event has no target")
            return False

        success: bool = False
        element_handle: ElementHandle | None = None

        max_highlight_duration_ms: int = 500
        min_highlight_duration_ms: int = 200
        highlight_duration_ms: int = min(
            (
                event.delay
                if hasattr(event, "delay") and event.delay is not None
                else max_highlight_duration_ms
            ),
            max_highlight_duration_ms,
        )
        highlight_duration_ms = max(highlight_duration_ms, min_highlight_duration_ms)

        try:
            element_handle: ElementHandle | None = await self._get_element_from_target(
                target
            )
            if element_handle:
                coords = await self.browser.page.evaluate(
                    """(element) => {
                        const rect = element.getBoundingClientRect();
                        return [rect.x + rect.width/2, rect.y + rect.height/2];
                    }""",
                    element_handle,
                )

                if coords and len(coords) == 2:
                    await self._highlight_element(
                        element_handle, event_index, timeout_ms=highlight_duration_ms
                    )
                    await self.browser.page.mouse.click(coords[0], coords[1])
                    success = True

        except Exception as e:
            logger.error(f"Error in _replay_click_event: {e}")

        if not success:
            await self._clear_previous_highlight()
            error_msg: str = (
                "Failed to click element - could not find or interact with the element"
            )
            logger.error(error_msg)
            logger.error("Target info:")

        return success

    async def _replay_scroll_event(self, event: "ScrollEvent") -> bool:
        """
        Replays a scroll event by scrolling to the specified coordinates.
        Uses smooth scrolling with a duration matching the event's delay.
        """
        try:
            x: int = event.scroll_x
            y: int = event.scroll_y
            logger.info(f"Smooth scrolling to position: X={x}, Y={y}")

            smooth_scroll_script: str = f"""
                (() => {{
                    const startX = window.pageXOffset || document.documentElement.scrollLeft;
                    const startY = window.pageYOffset || document.documentElement.scrollTop;
                    const distX = {x} - startX;
                    const distY = {y} - startY;
                    const duration = {event.delay};
                    const startTime = performance.now();
                    
                    function easeInOutQuad(t) {{ 
                        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; 
                    }}
                    
                    function scroll() {{
                        const elapsed = performance.now() - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const easeProgress = easeInOutQuad(progress);
                        
                        window.scrollTo(
                            startX + distX * easeProgress,
                            startY + distY * easeProgress
                        );
                        
                        if (progress < 1) {{
                            window.requestAnimationFrame(scroll);
                        }}
                    }}
                    
                    window.requestAnimationFrame(scroll);
                }})();
            """
            await self.browser.page.evaluate(smooth_scroll_script)
            await asyncio.sleep(event.delay / 1000 + 0.1)
            return True
        except Exception as e:
            logger.error(f"Error in _replay_scroll_event: {e}")
            return False

    async def _replay_input_event(self, event: InputEvent, event_index: int) -> bool:
        """Replays an input event using the element handle from _get_element_from_target."""
        if not event.target:
            logger.warning("Input event has no target")
            return False

        logger.info(
            f"Input: value={event.value}, checked={event.checked}, "
            + f"target={event.target.tag_name} {event.target.id} {event.target.class_name}"
        )

        try:
            element_handle: ElementHandle | None = await self._get_element_from_target(
                event.target
            )
            if not element_handle:
                logger.warning("Could not find element for input event target")
                return False

            await self._highlight_element(element_handle, event_index)

            if event.time_taken > 0 and len(event.value) > 1:
                delay_per_char: float = event.time_taken / (len(event.value) * 1000)

                for i in range(len(event.value)):
                    await element_handle.fill(event.value[: i + 1])
                    if i < len(event.value) - 1:
                        await asyncio.sleep(delay_per_char)
            else:
                await element_handle.fill(event.value)

            if event.checked is not None:
                await element_handle.evaluate(
                    f"element => element.checked = {str(event.checked).lower()}"
                )

            await self._capture_screenshot(event_index)

            await self._auto_clear_highlight(300)

            return True

        except Exception as e:
            logger.error(f"Error in _replay_input_event: {e}")
            return False

    async def _replay_change_event(
        self, event: "ChangeEvent", event_index: int
    ) -> bool:
        """Replays a change event using the element handle from _get_element_from_target."""
        if not event.target:
            logger.warning("Change event has no target")
            return False

        logger.info(
            f"Change: value={event.value}, checked={event.checked}, "
            + f"target={event.target.tag_name} {event.target.id} {event.target.class_name}"
        )

        try:
            element_handle: ElementHandle | None = await self._get_element_from_target(
                event.target
            )
            if not element_handle:
                logger.warning("Could not find element for change event target")
                return False

            await self._highlight_element(element_handle, event_index, timeout_ms=250)

            await self._fill_element(element_handle, event.value, event.checked)

            await self.browser.page.evaluate(
                """(element) => {
                    const event = new Event('change', { bubbles: true });
                    element.dispatchEvent(event);
                }""",
                element_handle,
            )

            return True

        except Exception as e:
            logger.error(f"Error in _replay_change_event: {e}")
            return False

    async def _clear_previous_highlight(self) -> None:
        """
        Removes any existing highlight from previously interacted elements.
        """
        await self.browser.page.evaluate(
            """
            const prevHighlight = document.getElementById('speck-element-highlight');
            if (prevHighlight) {
                prevHighlight.remove();
            }
            """
        )

    async def _highlight_element(
        self, element, event_index: int = -1, timeout_ms: int = None
    ) -> None:
        """
        Adds a red bounding box highlight to the specified element.
        This highlight will remain until the next interaction occurs or timeout expires.

        Args:
            element: The playwright element to highlight (ElementHandle) or a selector string
            event_index: The index of the current event
            timeout_ms: If provided, the highlight will be automatically removed after this many milliseconds
                        with a fade effect (half time visible, half time fading out)
        """
        await self._clear_previous_highlight()
        logger.info(f"Highlighting element at event {event_index}")

        if isinstance(element, str):
            element_str = repr(element)  # Properly escape the string for JS
            await self.browser.page.evaluate(
                f"""
                () => {{
                    // Find the element by selector or ID
                    let el;
                    const selectorStr = {element_str};
                    
                    if (selectorStr.startsWith('#') && selectorStr.includes(':')) {{
                        // For IDs with special characters
                        const id = selectorStr.substring(1);
                        el = document.getElementById(id);
                    }} else {{
                        try {{
                            el = document.querySelector(selectorStr);
                        }} catch (e) {{
                            console.error('Error with selector:', e);
                            return;
                        }}
                    }}
                    
                    if (!el) {{
                        console.error('Element not found with selector: ' + selectorStr);
                        return;
                    }}
                    
                    // Get element position and dimensions
                    const rect = el.getBoundingClientRect();
                    
                    // Create highlight element
                    const highlight = document.createElement('div');
                    highlight.id = 'speck-element-highlight';
                    highlight.style.position = 'absolute';
                    highlight.style.left = rect.left + window.scrollX + 'px';
                    highlight.style.top = rect.top + window.scrollY + 'px';
                    highlight.style.width = rect.width + 'px';
                    highlight.style.height = rect.height + 'px';
                    highlight.style.border = '2px solid red';
                    highlight.style.boxSizing = 'border-box';
                    highlight.style.pointerEvents = 'none'; // Don't interfere with clicks
                    highlight.style.zIndex = '10000'; // Ensure it's on top
                    highlight.style.boxShadow = '0 0 5px rgba(255, 0, 0, 0.5)';
                    highlight.style.opacity = '1';
                    highlight.style.transition = 'opacity 0.3s ease-out'; // Default transition
                    
                    document.body.appendChild(highlight);
                }}
                """
            )
        else:
            await self.browser.page.evaluate(
                """
                (element) => {
                    // Get element position and dimensions
                    const rect = element.getBoundingClientRect();
                    
                    // Create highlight element
                    const highlight = document.createElement('div');
                    highlight.id = 'speck-element-highlight';
                    highlight.style.position = 'absolute';
                    highlight.style.left = rect.left + window.scrollX + 'px';
                    highlight.style.top = rect.top + window.scrollY + 'px';
                    highlight.style.width = rect.width + 'px';
                    highlight.style.height = rect.height + 'px';
                    highlight.style.border = '2px solid red';
                    highlight.style.boxSizing = 'border-box';
                    highlight.style.pointerEvents = 'none'; // Don't interfere with clicks
                    highlight.style.zIndex = '10000'; // Ensure it's on top
                    highlight.style.boxShadow = '0 0 5px rgba(255, 0, 0, 0.5)';
                    highlight.style.opacity = '1';
                    highlight.style.transition = 'opacity 0.3s ease-out'; // Default transition
                    
                    document.body.appendChild(highlight);
                }
                """,
                element,
            )

        if timeout_ms:
            await self._auto_clear_highlight(timeout_ms)

    async def _auto_clear_highlight(self, timeout_ms: int) -> None:
        """
        Automatically clears the highlight after the specified timeout.
        The highlight will stay visible for timeout_ms/4 (25%), then fade out over timeout_ms*3/4 (75%).

        :param timeout_ms: The total time in milliseconds before the highlight is completely removed
        """
        first_quarter_sec: float = (timeout_ms * 0.25) / 1000.0
        await asyncio.sleep(first_quarter_sec)

        fade_duration_ms: int = int(timeout_ms * 0.75)
        fade_duration_ms = max(fade_duration_ms, 50)

        try:
            await self.browser.page.evaluate(
                f"""
                (() => {{
                    const highlight = document.getElementById('speck-element-highlight');
                    if (highlight) {{
                        highlight.style.transition = 'opacity {fade_duration_ms}ms ease-out';
                        highlight.style.opacity = '0';
                    }}
                }})()
                """
            )

            fade_duration_sec: float = fade_duration_ms / 1000.0
            await asyncio.sleep(fade_duration_sec)

            await self._clear_previous_highlight()
        except Exception as e:
            logger.debug(f"Error during highlight fade-out: {e}")
            await self._clear_previous_highlight()

    async def _capture_screenshot(self, event_index: int) -> Image:
        """
        Captures a screenshot with the current highlighted element.

        :param event_index: The index of the current event
        :param event_type: The type of event (click, scroll, etc.)
        :return: The base64-encoded screenshot data
        """
        screenshot_bytes: bytes = await self.browser.page.screenshot()
        screenshot_data: str = base64.b64encode(screenshot_bytes).decode()
        screenshot = Image(
            name=f"screenshot_{event_index}",
            data=screenshot_data,
            size=len(screenshot_data),
            type="image/png",
            source_url=None,
            annotation=None,
            description=None,
        )
        return screenshot

    async def _get_video_data(self, trim_duration_seconds: float) -> bytes | None:
        try:
            if not self.browser or not self.browser.session_dir:
                return None

            video_paths: list[Path] = list(
                Path(self.browser.session_dir).glob("*.webm")
            )
            if not video_paths:
                logger.warning("No video files found in session directory")
                return None

            video_path_obj: Path = video_paths[0]
            if not video_path_obj.exists() or video_path_obj.stat().st_size == 0:
                logger.error(f"Video file is empty or doesn't exist: {video_path_obj}")
                return None

            if trim_duration_seconds <= 0:
                with open(video_path_obj, "rb") as f:
                    return f.read()

            logger.info(
                f"Trimming video at path {video_path_obj} to {trim_duration_seconds} seconds"
            )

            trimmed_path: Path = video_path_obj.parent / "trimmed.webm"

            ffmpeg_cmd: list[str] = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i",
                str(video_path_obj),
                "-ss",
                f"{trim_duration_seconds:.3f}",  # Trim duration
                "-c:v",
                "vp9",  # VP9 codec
                "-crf",
                "35",  # Compression quality (higher = more compression)
                "-b:v",
                "0",  # Variable bitrate
                "-deadline",
                "realtime",  # Fast encoding
                "-cpu-used",
                "7",  # CPU optimization (0-8, higher = faster)
                "-row-mt",
                "1",  # Row-based multithreading
                "-tiles",
                "2x2",  # Tile-based encoding
                "-threads",
                "0",  # Auto thread count
                "-movflags",
                "+faststart",
                "-an",  # No audio
                "-sn",  # No subtitles
                "-f",
                "webm",  # Force WebM format
                str(trimmed_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Successfully trimmed video to temporary file")
                with open(trimmed_path, "rb") as f:
                    video_bytes: bytes = f.read()

                trimmed_path.unlink()
                return video_bytes
            else:
                logger.error(f"Error trimming video: {stderr.decode()}")
                with open(video_path_obj, "rb") as f:
                    return f.read()

        except Exception as e:
            logger.error(f"Error processing video data: {e}")
            return None

    async def _get_element_from_target(
        self, target: EventTarget
    ) -> ElementHandle | None:
        """
        Gets a Playwright ElementHandle from an EventTarget by trying multiple strategies.
        Uses direct JavaScript evaluation for special selectors like React IDs with colons.

        :param target: The EventTarget to get an element for
        :return: A Playwright ElementHandle if found, None otherwise
        """
        if not target:
            return None

        def escape_css_selector(selector: str) -> str:
            """
            Escape special characters in CSS selectors that might cause parsing issues.
            This handles characters like colons, semicolons, brackets, etc.
            """
            if not selector or selector.startswith("xpath="):
                return selector

            if ":" in selector or "[" in selector or "]" in selector:
                return f"js:{selector}"

            return selector

        selectors: list[tuple[str, str]] = []
        if target.css_selector:
            selectors.append(("CSS selector", escape_css_selector(target.css_selector)))
        if target.xpath:
            selectors.append(("XPath", f"xpath={target.xpath}"))
        if target.id:
            selectors.append(("ID", escape_css_selector(f"#{target.id}")))

        for selector_type, selector in selectors:
            try:
                if selector.startswith("js:"):
                    raw_selector: str = selector[3:]  # Remove the "js:" prefix

                    if raw_selector.startswith("#") and ":" in raw_selector:
                        element_id: str = raw_selector[1:]  # Remove the #

                        is_found_by_id: bool = await self.browser.page.evaluate(
                            f"document.getElementById('{element_id}') !== null"
                        )

                        if is_found_by_id:
                            element: ElementHandle = (
                                await self.browser.page.evaluate_handle(
                                    f"document.getElementById('{element_id}')"
                                )
                            )
                            return element

                    try:
                        escaped_element: ElementHandle = await self.browser.page.evaluate_handle(
                            f"""() => {{
                                try {{
                                    const selector = CSS.escape('{raw_selector.replace("'", "\\'")}');
                                    return document.querySelector(selector);
                                }} catch (e) {{
                                    return document.querySelector('{raw_selector.replace("'", "\\'")}');
                                }}
                            }}"""
                        )

                        is_null: bool = await self.browser.page.evaluate(
                            "(el) => el === null", escaped_element
                        )

                        if not is_null:
                            return escaped_element
                    except Exception as e:
                        logger.debug(f"Error using CSS.escape: {e}")

                    try:
                        direct_element: ElementHandle = await self.browser.page.evaluate_handle(
                            f"""() => {{
                                return document.querySelector('{raw_selector.replace("'", "\\'")}');
                            }}"""
                        )

                        is_null: bool = await self.browser.page.evaluate(
                            "(el) => el === null", direct_element
                        )

                        if not is_null:
                            return direct_element
                    except Exception as e:
                        logger.debug(f"Error using direct querySelector: {e}")
                else:
                    element = await self.browser.page.wait_for_selector(
                        selector, timeout=2000
                    )
                    if element:
                        return element

            except Exception as e:
                logger.debug(f"Failed to find element using {selector_type}: {e}")

        if target.tag_name and target.inner_text:
            try:
                text_to_find: str = target.inner_text
                if len(text_to_find) > 50:
                    text_to_find = text_to_find[
                        :50
                    ]  # Use just the first part of long text

                for text_finder in [
                    f"text='{text_to_find}'",  # Exact match
                    f"text='{text_to_find.split(' ')[0]}'",  # First word
                    f":text-matches('{text_to_find}', 'i')",  # Case-insensitive match
                ]:
                    try:
                        element = await self.browser.page.wait_for_selector(
                            text_finder, timeout=2000
                        )
                        if element:
                            return element
                    except Exception as e:
                        logger.debug(
                            f"Failed to find element using text finder {text_finder}: {e}"
                        )
            except Exception as e:
                logger.debug(f"Text-based element finding failed: {e}")

        logger.info("Element: null")
        logger.warning(
            f"Could not find element using any strategy. Target info: {target.model_dump_json()}"
        )
        return None

    async def _fill_element(
        self, element_handle: ElementHandle, value: str, checked: bool | None = None
    ) -> str:
        """
        Fills a form input with a value, optionally setting checked state for checkboxes/radios.
        Uses the element handle directly instead of selectors.
        :param element_handle: The element handle to fill
        :param value: The value to fill the element with
        :param checked: The checked state to set for checkboxes/radios
        :return: A string describing the action taken
        """
        try:
            element_info = await self.browser.page.evaluate(
                """(element) => ({
                    tagName: element.tagName.toLowerCase(),
                    type: element.type?.toLowerCase() || '',
                    isInput: element instanceof HTMLInputElement,
                    isTextArea: element instanceof HTMLTextAreaElement,
                    isSelect: element instanceof HTMLSelectElement
                })""",
                element_handle,
            )

            if element_info["isInput"]:
                if checked is not None and element_info["type"] in [
                    "checkbox",
                    "radio",
                ]:
                    await element_handle.evaluate(
                        f"element => element.checked = {str(checked).lower()}"
                    )
                    return f"Set checked state to {checked}"
                else:
                    await element_handle.fill(value)
                    return f"Filled input with value: {value}"
            elif element_info["isTextArea"]:
                await element_handle.fill(value)
                return f"Filled textarea with value: {value}"
            elif element_info["isSelect"]:
                await element_handle.select_option(value)
                return f"Selected option with value: {value}"
            else:
                await element_handle.evaluate(f"element => element.value = '{value}'")
                return f"Set value on element: {value}"

        except Exception as e:
            logger.error(f"Error filling element: {e}")
            return f"Failed to fill element: {e}"

    async def _save_data_to_disk(self, video_data: bytes | None) -> None:
        """
        Saves video data and screenshots to disk in the temp_output/timestamp directory.
        :param video_data: The video data in bytes
        """
        try:
            base_dir: Path = Path("temp_output")
            base_dir.mkdir(exist_ok=True)

            timestamp: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir: Path = base_dir / timestamp
            output_dir.mkdir(exist_ok=True)

            if video_data:
                video_path: Path = output_dir / "recording.webm"
                with open(video_path, "wb") as f:
                    f.write(video_data)
                logger.info(f"Successfully saved video to disk at: {video_path}")

            screenshots_dir: Path = output_dir / "screenshots"
            screenshots_dir.mkdir(exist_ok=True)

            for i, event in enumerate(self.replayed_events):
                if event.screenshot:
                    screenshot_bytes: bytes = base64.b64decode(event.screenshot.data)

                    screenshot_path: Path = (
                        screenshots_dir / f"screenshot_{i}.{event.screenshot.extension}"
                    )
                    with open(screenshot_path, "wb") as f:
                        f.write(screenshot_bytes)
                    logger.info(f"Saved screenshot {i} to {screenshot_path}")

        except Exception as e:
            logger.error(f"Error saving data to disk: {e}")

    async def _replay_screenshot_event(
        self, event: ScreenshotEvent, event_index: int
    ) -> tuple[bool, Image | None]:
        """Replays a screenshot event by taking a screenshot of the viewport."""
        try:
            current_viewport: list[int] = await self.browser.page.evaluate(
                """() => [window.innerWidth, window.innerHeight]"""
            )
            current_scroll: list[int] = await self.browser.page.evaluate(
                """() => [window.scrollX, window.scrollY]"""
            )

            if (
                current_viewport[0] != event.viewport_size.width
                or current_viewport[1] != event.viewport_size.height
            ):
                logger.warning(
                    f"Current viewport size ({current_viewport[0]}, {current_viewport[1]}) does not match recorded size "
                    f"({event.viewport_size.width}, {event.viewport_size.height})"
                )

            if (
                current_scroll[0] != event.scroll_position.x
                or current_scroll[1] != event.scroll_position.y
            ):
                logger.warning(
                    f"Current scroll position ({current_scroll[0]}, {current_scroll[1]}) does not match recorded position "
                    f"({event.scroll_position.x}, {event.scroll_position.y})"
                )

            screenshot: Image = await self._capture_screenshot(event_index)
            return True, screenshot
        except Exception as e:
            logger.error(f"Error in _replay_screenshot_event: {e}")
            return False, None

    async def _replay_component_selection_event(
        self, event: ComponentSelectionEvent, event_index: int
    ) -> tuple[bool, Image | None]:
        """Replays a component selection event by highlighting the component and taking a screenshot."""
        if not event.target:
            logger.error("Component selection event has no target")
            return False, None

        element_handle: ElementHandle | None = await self._get_element_from_target(
            event.target
        )
        if not element_handle:
            logger.error("Could not find element for component selection event target")
            return False, None

        try:
            await self.browser.page.evaluate(
                "element => element.scrollIntoView({behavior: 'instant', block: 'center'})",
                element_handle,
            )

            await asyncio.sleep(0.2)

            padding: int = 10
            clip_data = await self.browser.page.evaluate(
                """({ element, padding }) => {
                    const rect = element.getBoundingClientRect();
                    const viewport = {
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                    
                    // Add padding but don't exceed viewport
                    // Use viewport-relative coordinates (no scrollX/Y)
                    const clip = {
                        x: Math.max(0, rect.left - padding),
                        y: Math.max(0, rect.top - padding),
                        width: Math.min(rect.width + padding * 2, viewport.width),
                        height: Math.min(rect.height + padding * 2, viewport.height)
                    };
                    
                    return clip;
                }""",
                {"element": element_handle, "padding": padding},
            )

            await self.browser.page.evaluate(
                "element => { element.style.outline = '2px dashed #0066ff'; element.style.outlineOffset = '2px'; }",
                element_handle,
            )

            screenshot_bytes: bytes = await self.browser.page.screenshot(clip=clip_data)
            screenshot = Image(
                name=f"screenshot_{event_index}.png",
                data=base64.b64encode(screenshot_bytes).decode(),
                size=len(screenshot_bytes),
                type="image/png",
            )

            await self.browser.page.evaluate(
                "element => { element.style.outline = ''; element.style.outlineOffset = ''; }",
                element_handle,
            )

            return True, screenshot

        except Exception as e:
            logger.error(f"Error in _replay_component_selection_event: {e}")
            return False, None


async def summarize_recording(
    recording: Recording, replay_response: ReplayResponse
) -> RecordingSummary:
    """
    Summarizes the recording and the replay response.
    :param recording: The recording to summarize
    :param replay_response: The replay response to summarize
    :return: The summary of the recording and the replay response
    """
    recorded_events: str = "\n".join(
        [event.xml(idx=i + 1) for i, event in enumerate(recording.events)]
    )

    system_prompt: str = SUMMARIZE_RECORDING_SYSTEM_PROMPT()
    user_prompt: str = SUMMARIZE_RECORDING_USER_PROMPT(
        recording.annotation, recorded_events
    )

    with open("user_prompt.txt", "w") as f:
        f.write(user_prompt)

    messages: list[dict[str, str]] = [
        {"role": "user", "content": user_prompt},
    ]

    screenshots: list[str] = []

    for _i, event in enumerate(replay_response.replayed_events):
        if event.screenshot:
            screenshots.append(event.screenshot)

    messages.extend(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Image {i + 1} of {len(screenshots)}",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image},
                },
            ],
        }
        for i, image in enumerate(screenshots)
    )
    response: RecordingSummary = await chat(
        Model.GEMINI_2_0_FLASH,
        system_prompt,
        messages,
        response_model=RecordingSummary,
    )
    return response


async def main():
    import json

    with open(
        "src/agents/utils/task/interfaces/browsing/test_data/events.json", "r"
    ) as f:
        data = json.load(f)

    if "recordings" in data:
        recordings = RecordingCollection(**data)
        if len(recordings.recordings) > 0:
            recording = recordings.recordings[0]
        else:
            logger.error("No recordings found in collection")
            return
    else:
        try:
            recording = Recording(**data)
            logger.info(f"Loaded single recording with {len(recording.events)} events")
            if recording.duration:
                logger.info(f"Recording duration: {recording.duration}ms")
            if recording.viewport_size:
                logger.info(
                    f"Recording viewport: {recording.viewport_size.width}x{recording.viewport_size.height}"
                )
        except Exception as e:
            logger.error(f"Failed to parse recording data: {e}")
            return

    player = RecordingPlayer(None)
    results: ReplayResponse = await player.replay_recording(
        recording, delay_multiplier=1.0
    )

    with open(
        "src/agents/utils/task/interfaces/browsing/temp_script_output/recording.json",
        "w",
    ) as f:
        json.dump(recording.model_dump(), f)
    with open(
        "src/agents/utils/task/interfaces/browsing/temp_script_output/results.json", "w"
    ) as f:
        json.dump(results.model_dump(), f)


async def test_2():
    with open(
        "src/agents/utils/task/interfaces/browsing/temp_script_output/recording.json",
        "r",
    ) as f:
        recording = Recording(**json.load(f))

    with open(
        "src/agents/utils/task/interfaces/browsing/temp_script_output/results.json", "r"
    ) as f:
        results = ReplayResponse(**json.load(f))

    summary = await summarize_recording(recording, results)
    logger.info("Summary:")
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(test_2())
