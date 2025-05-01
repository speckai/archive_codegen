from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class DebugGit:
    """Local version of Git for debug mode"""

    def __init__(self, task: "Task", created_repo_id: str):
        self.task = task
        self.created_repo_id = created_repo_id
        self.repo_id = -1
        self.token = "debug-token"

    @property
    def tokenized_clone_url(self) -> str:
        return "debug-url"

    async def check_for_changes(self) -> bool:
        """Checks if there are any changes to the repo, including untracked files."""
        res = await self.task.sandbox.run_command(
            "git status --porcelain",
        )
        return res.get("stdout", "") != ""

    async def get_limited_git_diffs(self) -> str:
        ignored_files = [
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "pnpm-lock.yaml",
            "bun.lock",
        ]
        ignore_pattern = " ".join([f"':(exclude){f}'" for f in ignored_files])
        cmd_result = await self.task.sandbox.run_command(
            f"git diff -- {ignore_pattern}",
        )
        git_diffs_str = cmd_result.stdout
        return self._format_diff(git_diffs_str)

    def _format_diff(self, diff_text: str) -> str:
        added_lines = []
        removed_lines = []
        all_lines = diff_text.split("\n")
        MAX_LINE_LENGTH = 300
        for line in all_lines:
            if line.startswith("+"):
                added_lines.append(line[:MAX_LINE_LENGTH])
            elif line.startswith("-"):
                removed_lines.append(line[:MAX_LINE_LENGTH])
        return (
            "ADDED:\n"
            + "\n".join(added_lines)
            + "\nREMOVED:\n"
            + "\n".join(removed_lines)
        )

    async def commit_and_push_to_branch(
        self, commit_message: str, commit_description: str, branch_name: str
    ):
        """Only commits locally in debug mode"""
        await self.task.sandbox.run_command(
            f"git add . && git commit -m '{commit_message}' -m '{commit_description}'",
        )
        print(f"Debug mode: Would push to branch {branch_name}")
