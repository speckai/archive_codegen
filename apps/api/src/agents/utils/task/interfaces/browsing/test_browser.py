import asyncio
import base64
import datetime
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from morphcloud.api import InstanceExecResponse
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from src.database import Database
from src.schemas.core.common.files import Image
from src.utils.logging import logger

CLICK_CIRCLE_DURATION_MS: int = 500  # ms


if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class TestBrowser:
    def __init__(
        self,
        task: "Task",
        resolution: tuple[int, int],
        debug: bool = False,
        base_url: str = "",
    ):
        self.task: Task | None = task
        self.resolution: tuple[int, int] = resolution
        self.debug: bool = debug
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.recording: bool = False
        self.test_start_time: str | None = None
        self.playwright: Playwright | None = None
        self.last_mouse_position: dict[str, int] = {"x": 0, "y": 0}
        self.base_url: str = self.task.sandbox.preview_url if self.task else base_url
        self.temp_dir: Path | None = None

    async def start(self):
        """Starts the browser and creates a new page."""
        browser_storage: dict[str, str] = {}
        if self.task:
            browser_storage = Database.get_repo_property(
                self.task.git.repo_id, "browser_storage"
            )

        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.temp_dir / self.test_start_time

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

        self.context = await self.browser.new_context(
            record_video_dir=str(self.session_dir),
            record_video_size={
                "width": self.resolution[0],
                "height": self.resolution[1],
            },
            viewport={
                "width": self.resolution[0],
                "height": self.resolution[1],
            },
        )

        self.page = await self.context.new_page()
        self.recording = True

        if self.task:
            if browser_storage and "cookies" in browser_storage:
                logger.info(f"Setting cookies for {self.base_url}")
                for name, value in browser_storage["cookies"].items():
                    await self.page.context.add_cookies(
                        [
                            {
                                "name": name,
                                "value": value,
                                "url": self.base_url,
                            }
                        ]
                    )

        async def handle_storage(route):
            if browser_storage and "localStorage" in browser_storage:
                for key, value in browser_storage["localStorage"].items():
                    try:
                        await self.page.evaluate(
                            """({ key, value }) => {
                                try {
                                    localStorage.setItem(key, value);
                                    return true;
                                } catch (e) {
                                    console.error('Failed to set localStorage:', e);
                                    return false;
                                }
                            }""",
                            {"key": key, "value": value},
                        )
                    except Exception as e:
                        logger.error(f"Failed to set localStorage item: {e}")
            await route.continue_()

        if browser_storage:
            await self.page.route("**", lambda route: handle_storage(route))

    async def stop(self):
        """Closes the page and cleans up temporary files."""
        if self.context:
            await self.context.close()
        if self.browser is not None:
            await self.browser.close()
        if self.playwright is not None:
            await self.playwright.stop()

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    async def stop_recording(self):
        """Stops the video recording."""
        if self.context:
            await self.context.close()
            self.recording = False
            self.context = None

    async def navigate_to_url(self, url: str) -> None:
        await self.page.goto(url, wait_until="load", referer=self.base_url)
        logger.info(f"Navigated to {url}")

    async def action_mouse_button(
        self, coords: list[int], action: Literal["down", "up"]
    ):
        """Moves the mouse to the given coordinates and either puts mouse button down or up."""
        if not coords or len(coords) != 2:
            raise ValueError(
                f"Coordinates must be a [x, y] list for mouse button {action}. Got: {coords}"
            )

        x, y = coords
        logger.info(f"Mouse button {action} at coordinates: ({x}, {y})")
        if action == "down":
            await self.page.mouse.down()
        else:
            await self.page.mouse.up()
        await asyncio.sleep(0.5)
        return f"Mouse button {action} at ({x}, {y})"

    async def show_click_circle(self, x: int, y: int) -> None:
        """
        Shows a click circle at the given coordinates.
        :param x: The x coordinate of the click circle
        :param y: The y coordinate of the click circle
        """
        if self.debug and self.page:
            await self.page.evaluate(f"window.showClickCircle({x}, {y})")
            await asyncio.sleep(CLICK_CIRCLE_DURATION_MS / 1000)

    async def action_click(self, coords: list[int], button: str = "left") -> str:
        """
        Clicks at the given coordinates with the given button.
        :param coords: The coordinates to click
        :param button: The button to click (left, right, middle)
        :return: A string describing the click
        """
        if not coords:
            x, y = self.last_mouse_position["x"], self.last_mouse_position["y"]
            logger.info(f"Using last mouse position for click: ({x}, {y})")
        else:
            if len(coords) != 2:
                raise ValueError(
                    f"If provided, coordinates must be a [x, y] list for click. Got: {coords}"
                )
            x, y = coords
            logger.info(f"Clicking at coordinates: ({x}, {y}) with button='{button}'")

        if self.debug:
            await self.show_click_circle(x, y)
        await self.page.mouse.click(x, y, button=button)
        await asyncio.sleep(1)
        return f"Clicked at ({x}, {y}) with button='{button}'"

    async def action_double_click(self, coords: list[int]) -> str:
        """
        Double-clicks at the given coordinates.
        :param coords: The coordinates to double-click
        :return: A string describing the double-click
        """
        if not coords or len(coords) != 2:
            raise ValueError(
                f"Coordinates must be a [x, y] list for double_click. Got: {coords}"
            )

        x, y = coords
        logger.info(f"Double clicking at coordinates: ({x}, {y})")
        if self.debug:
            await self.show_click_circle(x, y)
            await asyncio.sleep(0.1)
            await self.show_click_circle(x, y)
        await self.page.mouse.dblclick(x, y)
        await asyncio.sleep(1)
        return f"Double clicked at ({x}, {y})"

    async def action_triple_click(self, coords: list[int]) -> str:
        """
        Triple-clicks at the given coordinates.
        :param coords: The coordinates to triple-click
        :return: A string describing the triple-click
        """
        if not coords or len(coords) != 2:
            raise ValueError(
                f"Coordinates must be a [x, y] list for triple_click. Got: {coords}"
            )

        x, y = coords
        logger.info(f"Triple clicking at coordinates: ({x}, {y})")
        if self.debug:
            await self.show_click_circle(x, y)
            await asyncio.sleep(0.1)
            await self.show_click_circle(x, y)
            await asyncio.sleep(0.1)
            await self.show_click_circle(x, y)
        await self.page.mouse.click(x, y, click_count=3)
        await asyncio.sleep(1)
        return f"Triple clicked at ({x}, {y})"

    async def action_drag(self, coords: list[int], target_coords: list[int]) -> str:
        """
        Drags from the given coordinates to the target coordinates.
        :param coords: The coordinates to drag from
        :param target_coords: The coordinates to drag to
        :return: A string describing the drag
        """
        if not coords or len(coords) != 2:
            raise ValueError(
                f"Missing or invalid 'coordinates' for drag action. {coords}"
            )
        if not target_coords or len(target_coords) != 2:
            raise ValueError(
                f"Missing or invalid 'target_coordinates' for drag action. {target_coords}"
            )

        start_x, start_y = coords
        end_x, end_y = target_coords
        logger.info(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        await self.page.mouse.move(end_x, end_y)
        await self.page.mouse.up()
        await asyncio.sleep(1)
        return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"

    async def action_hold_key(self, key: str, duration: int) -> str:
        """
        Holds the given key for the specified duration.
        :param key: The key to hold
        :param duration: The duration to hold the key
        :return: A string describing the hold
        """
        if not key:
            raise ValueError("Hold key action requires 'key'.")
        if duration is None:
            raise ValueError("Hold key action requires 'duration'.")

        logger.info(f"Holding key {key} for {duration} seconds")
        await self.page.keyboard.down(key)
        await asyncio.sleep(duration)
        await self.page.keyboard.up(key)
        return f"Held key {key} for {duration} seconds"

    async def action_type(self, text: str) -> str:
        """
        Types the given text on the page (wherever focus is).
        :param text: The text to type
        :return: A string describing the typing
        """
        if not text:
            raise ValueError("Typing action requires 'text'.")
        logger.info(f"Typing text: {text}")
        await self.page.keyboard.type(text)
        await asyncio.sleep(0.5)
        return f"Typed text: {text}"

    async def action_press(self, key: str) -> str:
        """
        Presses a special key (e.g. "Enter", "Tab").
        Supports modifier keys like Control, Alt, Shift.
        :param key: The key to press
        :return: A string describing the press
        """
        if not key:
            raise ValueError("Press action requires 'key'.")

        # xdotool's `key` syntax -> playwright
        key_mapping = {
            "ctrl": "Control",
            "alt": "Alt",
            "shift": "Shift",
            "meta": "Meta",
            "backspace": "Backspace",
            "delete": "Delete",
            "enter": "Enter",
            "return": "Enter",
            "tab": "Tab",
            "esc": "Escape",
            "page_down": "PageDown",
            "page_up": "PageUp",
            "home": "Home",
            "end": "End",
            "insert": "Insert",
            "down": "ArrowDown",
            "up": "ArrowUp",
            "left": "ArrowLeft",
            "right": "ArrowRight",
            **{f"KP_{i}": f"Numpad{i}" for i in range(10)},  # Map KP_0 through KP_9
        }

        key_sequences: list[str] = key.strip().split()

        for sequence in key_sequences:
            if "+" in sequence:  # shift+tab -> ["Shift", "Tab"]
                keys: list[str] = sequence.split("+")
                keys = [key_mapping.get(k.lower(), k) for k in keys]

                for modifier in keys[:-1]:
                    await self.page.keyboard.down(modifier)

                await self.page.keyboard.press(keys[-1])

                for modifier in reversed(keys[:-1]):
                    await self.page.keyboard.up(modifier)
            else:
                mapped_key: str = key_mapping.get(sequence.lower(), sequence)
                logger.info(f"Pressing key: {mapped_key}")
                await self.page.keyboard.press(mapped_key)

            await asyncio.sleep(0.1)

        await asyncio.sleep(0.5)
        return f"Pressed key sequence: {key}"

    async def action_mouse_move(self, coords: list[int]) -> str:
        """
        Moves the mouse to the given coordinates without clicking.
        :param coords: The coordinates to move to
        :return: A string describing the move
        """
        if not coords or len(coords) != 2:
            raise ValueError(
                f"Coordinates must be a [x, y] list for mouse_move. Got: {coords}"
            )

        x, y = coords
        logger.info(f"Moving mouse to coordinates: ({x}, {y})")
        await self.page.mouse.move(x, y)
        self.last_mouse_position = {"x": x, "y": y}
        await asyncio.sleep(0.5)
        return f"Moved mouse to ({x}, {y})"

    async def action_scroll(
        self, direction: Literal["up", "down", "left", "right"], amount: int
    ) -> str:
        """
        Scrolls in the given direction by the specified amount of clicks.
        :param direction: The direction to scroll (up, down, left, right)
        :param amount: The amount of clicks to scroll
        :return: A string describing the scroll
        """
        if direction not in ["up", "down", "left", "right"]:
            raise ValueError(f"Invalid scroll direction: {direction}")

        pixels_per_click: int = 100
        pixel_amount: int = amount * pixels_per_click

        if direction in ["up", "down"]:
            scroll_x = 0
            scroll_y = -pixel_amount if direction == "up" else pixel_amount
        else:
            scroll_x = -pixel_amount if direction == "left" else pixel_amount
            scroll_y = 0

        logger.info(f"Scrolling {direction} by {amount} clicks ({pixel_amount} pixels)")
        await self.page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

        scroll_info: dict[str, int] = await self.page.evaluate(
            """
            () => ({
                currentX: window.pageXOffset || document.documentElement.scrollLeft,
                currentY: window.pageYOffset || document.documentElement.scrollTop,
                totalX: Math.max(
                    document.body.scrollWidth,
                    document.documentElement.scrollWidth,
                    document.body.offsetWidth,
                    document.documentElement.offsetWidth
                ) - window.innerWidth,
                totalY: Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.offsetHeight
                ) - window.innerHeight
            })
        """
        )

        await asyncio.sleep(0.5)
        if direction in ["up", "down"]:
            return f"Scrolled {direction} by {amount} clicks ({pixel_amount} pixels). Position: {int(scroll_info['currentY'])}/{int(scroll_info['totalY'])} pixels"
        else:
            return f"Scrolled {direction} by {amount} clicks ({pixel_amount} pixels). Position: {int(scroll_info['currentX'])}/{int(scroll_info['totalX'])} pixels"

    async def action_refresh(self) -> str:
        """
        Refreshes the current page and waits for it to load.
        :return: A string describing the refresh
        """
        logger.info("Refreshing page")
        await self.page.reload()
        await self.page.wait_for_load_state("load")
        await asyncio.sleep(3)  # Extra wait for dynamic content
        return "Page refreshed"

    async def inject_script(self, script: str) -> None:
        """
        Injects a script into the page.
        :param script: The script to inject
        """
        await self.page.add_init_script(script)

    async def take_screenshot(self, event_index: int) -> Image:
        """
        Takes a screenshot of the current page.

        :return: Base64-encoded screenshot data with data URL prefix
        """
        screenshot_bytes: bytes = await self.page.screenshot(
            full_page=False,
            type="png",
            clip=None,
            omit_background=False,
            quality=None,
        )
        screenshot_data: str = base64.b64encode(screenshot_bytes).decode()
        screenshot: Image = Image(
            name=f"screenshot_{event_index}",
            data=screenshot_data,
            size=len(screenshot_data),
            type="image/png",
            source_url=None,
            annotation=None,
            description=None,
        )
        return screenshot

    async def take_full_page_screenshot(self) -> list[Image]:
        """
        Takes a screenshot of the entire page.
        :return: A list of images containing the screenshot data and scroll position
        """
        page_height: int = await self.page.evaluate(
            "document.documentElement.scrollHeight"
        )
        viewport_height: int = await self.page.evaluate("window.innerHeight")

        screenshots: list[Image] = []
        current_scroll: int = 0

        while current_scroll < page_height:
            await self.page.evaluate(f"window.scrollTo(0, {current_scroll})")
            await asyncio.sleep(0.3)

            screenshot_bytes: bytes = await self.page.screenshot()
            screenshot_data: str = base64.b64encode(screenshot_bytes).decode()

            screenshot: Image = Image(
                name=f"screenshot_{current_scroll}",
                data=screenshot_data,
                size=len(screenshot_data),
                type="image/png",
                source_url=None,
                annotation=None,
                description=None,
            )
            screenshots.append(screenshot)

            current_scroll += viewport_height

        await self.page.evaluate("window.scrollTo(0, 0)")

        return screenshots

    async def update_viewport_size(self, width: int, height: int) -> None:
        """
        Updates the viewport size of the browser.
        :param width: The new viewport width
        :param height: The new viewport height
        """
        if self.page:
            logger.info(f"Updating viewport size to: {width}x{height}")
            await self.page.set_viewport_size({"width": width, "height": height})

            self.resolution = (width, height)
        else:
            logger.warning("Cannot update viewport size: page not initialized")

    async def get_used_files(self) -> list[str]:
        """
        Extracts file paths used by the application from source maps.

        :return: A list of file paths used by the application
        """
        if not self.page or not self.task:
            logger.warning("Cannot get used files: page or task not initialized")
            return []

        source_paths: list[str] = []
        cdp_session = await self.page.context.new_cdp_session(self.page)

        await cdp_session.send("Page.enable")
        await cdp_session.send("Network.enable")

        js_files: list[str] = await self.page.evaluate(
            """
            () => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.map(script => script.src);
            }
            """
        )

        for js_url in js_files:
            logger.info(f"Checking {js_url}")
            chunk_name: str | None = self._extract_chunk_name(js_url)

            if chunk_name:
                converted_path: str | None = self._convert_chunk_to_path(chunk_name)
                if (
                    converted_path
                    and converted_path not in source_paths
                    and "node_modules" not in converted_path
                ):
                    source_paths.append(converted_path)

            try:
                js_content: str | None = await self.page.evaluate(
                    f"""
                    async () => {{
                        try {{
                            const response = await fetch('{js_url}');
                            return await response.text();
                        }} catch (e) {{
                            return null;
                        }}
                    }}
                    """
                )

                if not js_content:
                    continue

                source_map_url: str | None = None
                sourcemap_match: re.Match | None = re.search(
                    r"//# sourceMappingURL=(.+)$", js_content, re.MULTILINE
                )

                if sourcemap_match:
                    source_map_url = sourcemap_match[1]

                    if not source_map_url.startswith("http"):
                        base_url = js_url.rsplit("/", 1)[0] if "/" in js_url else js_url
                        source_map_url = f"{base_url}/{source_map_url}"

                    if source_map_url.startswith("data:application/json;base64,"):
                        base64_data = source_map_url.split("base64,")[1]
                        try:
                            decoded_data = base64.b64decode(base64_data).decode("utf-8")
                            source_map_content = json.loads(decoded_data)
                            if "sources" in source_map_content:
                                for source in source_map_content["sources"]:
                                    if (
                                        source not in source_paths
                                        and "node_modules" not in source
                                    ):
                                        source_with_file_ext = re.sub(
                                            r"\.(js|tsx|ts|jsx|mjs|png|jpg|svg|gif|css)$",
                                            ".file",
                                            source,
                                        )
                                        if (
                                            source == source_with_file_ext
                                            and not source.endswith(".file")
                                        ):
                                            source_with_file_ext = f"{source}.file"
                                        source_paths.append(source_with_file_ext)
                        except Exception as e:
                            logger.error(f"Error processing base64 source map: {e}")
                        continue

                    if source_map_url.startswith("data:"):
                        continue

                    try:
                        source_map_content: str | None = await self.page.evaluate(
                            f"""
                            async () => {{
                                try {{
                                    const response = await fetch('{source_map_url}');
                                    return await response.json();
                                }} catch (e) {{
                                    return null;
                                }}
                            }}
                            """
                        )

                        if source_map_content and "sources" in source_map_content:
                            for source in source_map_content["sources"]:
                                if (
                                    source not in source_paths
                                    and "node_modules" not in source
                                ):
                                    source_with_file_ext = re.sub(
                                        r"\.(js|tsx|ts|jsx|mjs|png|jpg|svg|gif|css)$",
                                        ".file",
                                        source,
                                    )
                                    if (
                                        source == source_with_file_ext
                                        and not source.endswith(".file")
                                    ):
                                        source_with_file_ext = f"{source}.file"
                                    source_paths.append(source_with_file_ext)
                    except Exception as e:
                        logger.error(f"Error fetching source map: {e}")
            except Exception as e:
                logger.error(f"Error processing JS file {js_url}: {e}")

        result: dict[str, str] = {}

        logger.info("Searching for files")

        find_command: str = (
            'find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*"'
        )
        find_result: InstanceExecResponse = await self.task.terminal.run_command(
            f"cd /repo && {find_command}"
        )

        if find_result and find_result.stdout:
            all_files: list[str] = find_result.stdout.splitlines()

            for source_path in source_paths:
                if source_path.endswith(".file"):
                    search_path: str = source_path[:-5]
                else:
                    search_path: str = source_path

                path_parts: list[str] = [p for p in search_path.split("/") if p]

                if len(path_parts) >= 3:
                    search_pattern: str = (
                        f"{path_parts[-3]}/{path_parts[-2]}/{path_parts[-1]}"
                    )
                elif len(path_parts) >= 2:
                    search_pattern = f"{path_parts[-2]}/{path_parts[-1]}"
                else:
                    search_pattern = path_parts[-1] if path_parts else ""

                if not search_pattern:
                    continue

                matches: list[str] = []
                matches.extend(
                    file_path for file_path in all_files if search_pattern in file_path
                )

                if matches:
                    matches.sort(key=len)
                    result[source_path] = matches[0]

        processed_paths: list[str] = []

        for real_path in result.values():
            processed_file_path: str = real_path

            if self.task.sandbox.subdirectory:
                normalized_path: str = os.path.normpath(
                    os.path.join(self.task.sandbox.subdirectory, processed_file_path)
                )
            else:
                normalized_path: str = os.path.normpath(processed_file_path)
            processed_paths.append(normalized_path)

        return processed_paths

    def _extract_chunk_name(self, url: str) -> str | None:
        """Extract the chunk name from a script URL."""
        filename = url.split("/")[-1]

        if "?" in filename:
            filename = filename.split("?")[0]

        app_pattern: str = r"_next/static/chunks/(app/.*)\.(js|tsx|ts|jsx|mjs|css)$"
        app_match: re.Match | None = re.search(app_pattern, url)
        if app_match:
            return f"{app_match.group(1)}.file"

        chunk_patterns: list[str] = [
            r"_next/static/chunks/([a-zA-Z0-9_]+)_.+\.js$",
            # Pattern like: bundle.js
            r"(bundle)\.js$",
            # Pattern like: main-app.js
            r"(main-app)\.js$",
            # Pattern for webpack chunks
            r"static/js/([^.]+)\.[a-f0-9]+\.chunk\.js$",
            # Pattern for other common chunk formats
            r"static/js/([^.]+)\.js$",
            # Pattern for CSS files
            r"static/css/([^.]+)\.css$",
            # General Next.js chunks pattern as fallback
            r"_next/static/chunks/(.+)\.js$",
        ]

        for pattern in chunk_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _convert_chunk_to_path(self, chunk_name: str) -> str | None:
        """Convert a chunk name to a file path."""

        if chunk_name in {"bundle", "main-app", "main", "vendor", "runtime"}:
            return None

        if chunk_name.endswith(".file"):
            return chunk_name
        if "/" in chunk_name:
            if re.search(r"\.(js|tsx|ts|jsx|mjs|png|jpg|svg|gif|css)$", chunk_name):
                return re.sub(
                    r"\.(js|tsx|ts|jsx|mjs|png|jpg|svg|gif|css)$", ".file", chunk_name
                )
            return f"{chunk_name}.file"
        path_parts: list[str] = chunk_name.split("_")

        common_extensions: list[str] = [
            "tsx",
            "jsx",
            "ts",
            "js",
            "mjs",
            "png",
            "jpg",
            "svg",
            "gif",
            "css",
        ]

        file_path: str = ""
        i: int = 0
        extension_found: bool = False

        while i < len(path_parts):
            part: str = path_parts[i]

            if part in common_extensions and i > 0:
                file_path = file_path.rstrip("/")
                file_path += ".file"
                extension_found = True
                break
            else:
                file_path += f"{part}/"
                i += 1

        if not extension_found:
            file_path = file_path.rstrip("/")

            last_part: str = path_parts[-1] if path_parts else ""
            for ext in common_extensions:
                if last_part.endswith(ext) and len(last_part) > len(ext):
                    base_name: str = last_part[: -len(ext)]
                    file_path = file_path[: -len(last_part)] + base_name + ".file"
                    extension_found = True
                    break

        if not extension_found:
            file_path = re.sub(r"\/[0-9a-f]{8,}$", "", file_path)
            if not file_path.endswith(".file"):
                file_path += ".file"

        return file_path
