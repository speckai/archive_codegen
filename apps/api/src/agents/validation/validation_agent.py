from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from src.agents.utils.base_agent import BaseAgent
from src.agents.validation.console_tester import ConsoleTester
from src.agents.validation.utils.prompts import (
    URL_GENERATION_PROMPT,
    URL_GENERATION_SYSTEM,
)
from src.agents.validation.visual.visual_tester import VisualTester
from src.schemas.core.validation import RuntimeResult, TestPlan, TestResult
from src.schemas.llm import Model

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

MAX_ITERATIONS: int = 15


class URLGenerator(BaseModel):
    reasoning: str = Field(
        ...,
        description="The reasoning for the URLs to test. We only need valid URLs, so don't include any invalid ones.",
    )
    url_paths: list[str] = Field(..., description="The list of URLs to test")


class ValidationAgent(BaseAgent):
    def __init__(
        self,
        task: "Task",
    ):
        super().__init__(task)
        self.console_tester = ConsoleTester(task, self)
        self.visual_tester = VisualTester(task, self)
        self.last_test_plan: TestPlan | None = None

    async def validate_changes(self) -> bool:
        test_plan: TestPlan = await self._get_test_plan()

        self.last_test_plan = test_plan

        # console_test_result: bool = await self.console_tester.perform_console_log_test(test_plan)
        console_test_result: bool = True

        visual_test_result: bool = await self.visual_tester.perform_visual_test(
            test_plan
        )
        return console_test_result and visual_test_result

    async def _get_test_plan(self) -> TestPlan:
        file_tree: str = await self.task.file_system.get_all_tracked_file_path_trees()

        git_diffs: str = await self.task.git.get_last_commit_diff()

        issue_description: str = self.task.issue_creation_agent.issue_description

        # Generate URLs from diffs instead of getting all possible URLs
        # If there are test cases in the bug report, use them
        bug_report = self.task.initial_context_agent.bug_report
        test_cases = (
            bug_report.test_cases
            if bug_report and hasattr(bug_report, "test_cases")
            else []
        )
        website_urls = await self.task.website.get_possible_urls()

        # Generate URLs from diffs
        test_url_generator: URLGenerator = await self.llm_response(
            model_type=Model.GEMINI_2_0_FLASH,
            system=URL_GENERATION_SYSTEM(),
            message=URL_GENERATION_PROMPT(
                issue_description=issue_description,
                diffs=git_diffs,
                file_tree=file_tree,
                all_valid_urls=",".join(website_urls),
                test_cases="\n".join(
                    [test_case.model_dump_json(indent=3) for test_case in test_cases]
                ),
            ),
            response_model=URLGenerator,
        )

        if website_urls:
            test_url_generator.url_paths.extend(website_urls)
            # Remove duplicates while preserving order
            test_url_generator.url_paths = list(
                dict.fromkeys(test_url_generator.url_paths)
            )

        test_plan: TestPlan = TestPlan(
            thinking="",
            test_cases=test_cases,
            urls_to_test=test_url_generator.url_paths,
        )

        print(test_plan.model_dump_json(indent=3))

        return test_plan

    async def collect_validation_data(
        self,
    ) -> tuple[list[TestResult], list[RuntimeResult], TestPlan | None]:
        """
        Collect raw validation data from both visual and console tests.
        Returns the raw data that can be formatted as needed.
        """
        visual_results: list[TestResult] = (
            self.visual_tester.last_results
            if hasattr(self.visual_tester, "last_results")
            else []
        )
        console_results: list[RuntimeResult] = self.console_tester.last_runtime_results
        test_plan = self.last_test_plan

        return visual_results, console_results, test_plan
