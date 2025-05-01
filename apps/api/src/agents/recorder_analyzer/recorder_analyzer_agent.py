from typing import TYPE_CHECKING

from src.agents.recorder_analyzer.utils.models import (
    StructuredConsoleLogInfo,
)
from src.agents.recorder_analyzer.utils.search_utils import (
    convert_to_file_locations,
    extract_top_files,
    search_codebase_for_keywords,
    search_files_by_pattern,
)
from src.agents.utils.base_agent import BaseAgent
from src.schemas.core.common.recordings import (
    ConsoleLog,
)
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

CONSOLE_LOG_ANALYZER_SYSTEM_PROMPT = """You are a specialized code analyzer that extracts structured information from browser console logs.
Your task is to analyze console logs from a recording session and extract relevant file paths, line numbers, and other 
useful information for debugging and understanding the code that generated these logs.
""".strip()

CONSOLE_LOG_ANALYZER_USER_PROMPT = """
I need you to analyze these console logs from a browser recording session.

<console_logs>
{console_logs}
</console_logs>

For each console log, extract:
1. File paths mentioned in the logs or tracebacks
2. Line numbers mentioned in the logs or tracebacks
3. Key error messages and their types
4. Non-library functions or variables for codebase search

If you see webpack paths like 'webpack-internal:///(app-pages-browser)/./app/login/page.tsx', 
extract the actual file path (e.g., 'app/login/page.tsx').

Focus especially on extracting actionable information that would help debug the issues shown in the logs.

If there doesn't seem to be any relevant information in the logs, return an empty list which is a perfectly valid response. DON'T put a response without a reason because non-specific keywords will return a lot of results which will clutter the code analyzer.
""".strip()

TIMELINE_SUMMARY_SYSTEM_PROMPT = """You are an assistant that specializes in analyzing user interactions and browser events to produce 
concise, insightful summaries of what a user did and what went wrong in their session.
""".strip()

TIMELINE_SUMMARY_USER_PROMPT = """
I need you to create a concise summary of this recording timeline that shows user actions and console logs in chronological order.

<timeline>
{timeline}
</timeline>

The timeline contains user actions (clicks, inputs, scrolls) and console logs (including errors).

Based on this timeline:
1. Summarize what the user was trying to do
2. Identify any errors or issues that occurred
3. Note the sequence of key actions that led to problems
4. Create a list of the specific user actions taken

Avoid technical details unless they're critical for understanding what happened.
Focus on creating a clear, concise narrative of the user's experience and any problems encountered.
""".strip()


class RecorderAnalyzerAgent(BaseAgent):
    def __init__(self, task: "Task"):
        super().__init__(task)

    async def keyword_search_on_console_logs(
        self, console_logs: list[ConsoleLog]
    ) -> StructuredConsoleLogInfo:
        """
        Search for relevant files using keywords and add them as seed files.

        :param keywords: List of keywords to search for
        :param relevant_files: List of file locations that appear to be relevant
        :return: None
        """
        structured_console_log_info: StructuredConsoleLogInfo = (
            await self._extract_console_log_info(console_logs)
        )
        file_patterns = [
            file_loc.path for file_loc in structured_console_log_info.relevant_files
        ]
        keyword_results = await search_codebase_for_keywords(
            self.task, structured_console_log_info.keywords
        )
        fuzzy_matches = await search_files_by_pattern(self.task, file_patterns)
        top_files = extract_top_files(keyword_results, fuzzy_matches)

        for file_path in top_files:
            logger.debug(f"Adding seed file: {file_path}")
            self.task.code_analyzer_agent.add_referenced_file(file_path)

        logger.debug(f"Added {len(top_files)} seed files to code analyzer")

        updated_locations = convert_to_file_locations(keyword_results, top_files)
        existing_paths = {
            file_loc.path for file_loc in structured_console_log_info.relevant_files
        }
        for file_loc in updated_locations:
            if file_loc.path not in existing_paths:
                structured_console_log_info.relevant_files.append(file_loc)

        return structured_console_log_info

    async def _extract_console_log_info(
        self, console_logs: list[ConsoleLog]
    ) -> StructuredConsoleLogInfo:
        """
        Extract structured information from console logs using LLM.

        :param console_logs: List of console logs to analyze
        :return: StructuredConsoleLogInfo containing extracted information
        """
        if not console_logs:
            return StructuredConsoleLogInfo(
                reasoning="No console logs provided",
                relevant_files=[],
                keywords=[],
            )

        console_logs_xml = "\n".join([log.xml for log in console_logs])

        return await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=CONSOLE_LOG_ANALYZER_SYSTEM_PROMPT,
            message=CONSOLE_LOG_ANALYZER_USER_PROMPT.format(
                console_logs=console_logs_xml
            ),
            response_model=StructuredConsoleLogInfo,
        )
