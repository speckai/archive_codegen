from pydantic import BaseModel
from src.schemas.core.common.recordings import RecordingCollection
from src.schemas.core.common.user_reports import BugReport, IssueContents
from src.utils.prompt_utils import format_prompt


class Context(BaseModel):
    recordings: RecordingCollection | None = None
    bug_report: BugReport | None = None
    issue_contents: IssueContents | None = None

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <context>
            <bug_report>
            {self.bug_report.model_dump_json()}
            </bug_report>
            <issue_contents>
            {"N/A" if self.issue_contents is None else self.issue_contents.model_dump_json()}
            </issue_contents>
            </context>
            """
        )
