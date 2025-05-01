import traceback
from typing import TYPE_CHECKING

from github import Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository
from morphcloud.api import InstanceExecResponse
from pydantic import BaseModel
from src.agents.utils.task.interfaces.website import WebsitePullRequest
from src.database import Workspace
from src.github.utils import (
    get_github_token,
    get_issue_details,
    get_repo_installation_id,
)
from src.prompts.git import (
    COMMIT_SYSTEM_PROMPT,
    COMMIT_USER_PROMPT,
    GIT_BRANCH_SYSTEM_PROMPT,
    GIT_BRANCH_USER_PROMPT,
    PR_DESCRIPTION_SYSTEM,
    PR_DESCRIPTION_USER,
)
from src.schemas.core.common import (
    ChatMessageRole,
    CommitMessage,
    MainMessage,
    MessageData,
)
from src.schemas.core.common.git import GitBranch
from src.schemas.github import GitHubIssue
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class PullRequestItems(BaseModel):
    title: str
    body: str


class Git:
    def __init__(
        self,
        task: "Task",
        git_repo_id: int,
        workspace: Workspace,
        issue_number: int | None,
    ):
        self.task: "Task" = task
        self.repo_id: int = git_repo_id
        self.workspace: Workspace = workspace
        self.issue_number: int | None = issue_number

        # Skip GitHub initialization if in debug mode
        if self.task.debug:
            self._token = "debug-token"
            self.github = None
            self.repo = None
            return

        if self.repo_id == -1:
            return

        _github_installation_id: str = get_repo_installation_id(
            self.repo_id, self.task.user.id
        )

        self._token: str = get_github_token(_github_installation_id)
        self.github: Github = Github(self._token)

        try:
            self.repo: Repository = self.github.get_repo(self.repo_id)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"Error getting repo -- check installation ID: {e}")
            raise e

    @property
    def tokenized_clone_url(self) -> str:
        """Gets the clone url with the token to access the repo."""
        if self.task.debug:
            return "debug-url"
        return self.repo.clone_url.replace(
            "https://github.com/",
            f"https://x-access-token:{self.token}@github.com/",
        )

    @property
    def token(self) -> str:
        """
        Gets the token to access the repo.
        If the token is invalid, it will be refreshed.
        """
        return self._token

    def _format_diff(self, diff_text: str) -> str:
        added_lines: list[str] = []
        removed_lines: list[str] = []
        all_lines: list[str] = diff_text.split("\n")
        MAX_LINE_LENGTH: int = 300
        for line in all_lines:
            if line.startswith("+"):
                added_lines.append(line[:MAX_LINE_LENGTH])
            elif line.startswith("-"):
                removed_lines.append(line[:MAX_LINE_LENGTH])
        formatted_diff_text: str = (
            "ADDED:\n"
            + "\n".join(added_lines)
            + "\nREMOVED:\n"
            + "\n".join(removed_lines)
        )
        return formatted_diff_text

    async def check_for_changes(self) -> bool:
        """Checks if there are any changes to the repo, including untracked files."""
        res: InstanceExecResponse = await self.task.sandbox.run_command(
            "cd /repo && git status --porcelain",
        )
        return res.stdout != ""

    async def create_branch(self, issue_dict: dict) -> str | None:
        """Creates a new branch."""
        commands: list[str] = [
            'git config user.email "speck-engineer[bot]@users.noreply.github.com"',
            'git config user.name "speck-engineer[bot]"',
        ]

        for cmd in commands:
            await self.task.sandbox.run_command(cmd)

        branch_names: list[str] = await self.get_branch_names()

        git_branch: GitBranch = await self.task.llm_chat(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=GIT_BRANCH_SYSTEM_PROMPT(),
            message=GIT_BRANCH_USER_PROMPT(issue_dict, branch_names),
            response_model=GitBranch,
            caller="git",
        )
        branch_name: str = git_branch.branch_name
        if branch_name in branch_names:
            logger.error(f"Branch name {branch_name} already exists. Using num")
            unique_index: int = 1
            while f"{branch_name}-{unique_index}" in branch_names:
                unique_index += 1
            branch_name = f"{branch_name}-{unique_index}"

        await self.task.sandbox.run_command(
            f"cd /repo && git checkout -b {branch_name}",
        )
        return branch_name

    async def commit_changes(self) -> bool:
        """
        Commits the changes to the repo.
        :return: True if changes were committed, False otherwise.
        """
        if not await self.check_for_changes():
            logger.warning("No changes to commit")
            return False

        git_diffs: str = await self.get_limited_git_diffs()
        commit_message_obj: CommitMessage = await self.task.llm_chat(
            model_type=Model.GEMINI_2_0_FLASH,
            system=COMMIT_SYSTEM_PROMPT(),
            message=COMMIT_USER_PROMPT(
                diffs=git_diffs,
            ),
            response_model=CommitMessage,
            caller="git",
        )

        await self.task.sandbox.run_command(
            f"cd /repo && git add . && git commit -m '{commit_message_obj.commit_message}' -m '{commit_message_obj.commit_description}'",
        )

        if self.task.debug:
            logger.info(f"Debug mode: Would push {commit_message_obj.commit_message}")
            return False

        full_repo_name: str = self.repo.full_name
        await self.task.sandbox.run_command(
            f"cd /repo && git push https://x-access-token:{self.token}@github.com/{full_repo_name}.git",
            use_path=False,
        )

        return True

    async def get_pr_title_and_body(
        self,
        test_cases: dict,
        bug_report_dict: dict,
        issue_dict: dict,
    ) -> PullRequestItems:
        """Gets the PR title and body."""
        git_diffs: str = await self.get_limited_git_diffs()
        return await self.task.llm_chat(
            model_type=Model.GEMINI_2_0_FLASH,
            system=PR_DESCRIPTION_SYSTEM(),
            message=PR_DESCRIPTION_USER(
                bug_report_dict, issue_dict, test_cases, git_diffs, self.issue_number
            ),
            response_model=PullRequestItems,
            caller="git",
        )

    async def get_limited_git_diffs(self) -> str:
        ignored_files: list[str] = [
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "pnpm-lock.yaml",
            "bun.lock",
        ]

        ignore_pattern: str = " ".join([f"':(exclude){f}'" for f in ignored_files])
        tracked_diff: str = (
            await self.task.sandbox.run_command(
                "cd /repo && git diff -- {ignore_pattern}",
            )
        ).stdout

        untracked_files: str = (
            await self.task.sandbox.run_command(
                "cd /repo && git ls-files --others --exclude-standard"
            )
        ).stdout

        untracked_diffs: list[str] = []
        for file in untracked_files.splitlines():
            if any(ignored in file for ignored in ignored_files):
                continue
            try:
                content: str = (
                    await self.task.sandbox.run_command(f"cd /repo && cat {file}")
                ).stdout
                untracked_diffs.append(
                    f"diff --git a/{file} b/{file}\n"
                    f"new file mode 100644\n"
                    f"--- /dev/null\n"
                    f"+++ b/{file}\n"
                    + "\n".join(f"+{line}" for line in content.splitlines())
                )
            except Exception:
                continue

        combined_diff: str = tracked_diff + "\n" + "\n".join(untracked_diffs)

        file_sections: list[str] = combined_diff.split("diff --git")
        limited_sections: list[str] = [
            section[:50000] for section in file_sections if section.strip()
        ]

        git_diffs_str: str = "\n".join(limited_sections)
        git_diffs: str = self._format_diff(git_diffs_str)
        return git_diffs

    async def get_branch_names(self) -> list[str]:
        """
        Gets all branch names, including remote branches.
        :return: The branch names sorted by most recent commit (except current branch stays first).
        """
        if self.task.debug:
            print("Debug mode: Returning main")
            return ["main"]

        await self.task.sandbox.run_command("cd /repo && git fetch --prune")

        result: InstanceExecResponse = await self.task.sandbox.run_command(
            'cd /repo && git for-each-ref --sort=-committerdate refs/heads refs/remotes --format="%(refname:short)"'
        )

        branches: list[str] = [
            branch.strip('"').replace("remotes/", "").replace("origin/", "")
            for branch in result.stdout.split("\n")
            if branch and not branch.endswith("/HEAD")
        ]

        branches = list(dict.fromkeys(branches))

        if not branches:
            return ["main"]

        current_branch: InstanceExecResponse = await self.task.sandbox.run_command(
            "cd /repo && git branch --show-current"
        )
        current: str = current_branch.stdout.strip()
        if current in branches:
            branches.remove(current)
            branches.insert(0, current)

        return branches

    async def get_issue_object(self) -> GitHubIssue | None:
        if not self.issue_number or self.repo_id == -1:
            logger.info("No issue number or repository ID set for this task")
            return None

        try:
            logger.info(
                f"Fetching issue #{self.issue_number} from repository {self.repo_id}"
            )
            issue_data: GitHubIssue | None = await get_issue_details(
                self.repo_id, self.issue_number, self.task.user.id
            )

            if not issue_data:
                logger.error(
                    f"Issue #{self.issue_number} not found in repository {self.repo_id}"
                )
                return None

            logger.info(f"Successfully fetched issue: {issue_data.title}")
            return issue_data

        except Exception as e:
            logger.error(f"Error fetching issue details: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def add_issue_comment(self, comment_text: str) -> bool:
        if not self.issue_number or self.repo_id == -1:
            logger.warning("No issue number or repository ID set for this task")
            return False

        if self.task.debug:
            logger.info(
                f"Debug mode: Would add comment to issue #{self.issue_number}: {comment_text}"
            )
            return True

        try:
            if not self.repo:
                logger.error("Repository object not initialized")
                return False

            try:
                issue: Issue = self.repo.get_issue(self.issue_number)
                logger.info(f"Found issue #{self.issue_number} - {issue.title}")
            except Exception as e:
                logger.error(f"Failed to get issue #{self.issue_number}: {str(e)}")
                return False

            try:
                comment: IssueComment = issue.create_comment(comment_text)
                logger.info(
                    f"Added comment (ID: {comment.id}) to issue #{self.issue_number}"
                )
                return True
            except Exception as e:
                logger.error(
                    f"Failed to add comment to issue #{self.issue_number}: {str(e)}"
                )
                return False

        except Exception as e:
            logger.error(f"Error adding comment to issue: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def get_last_commit_diff(self) -> str:
        """
        Get the diff from the last commit.
        :return: Formatted diff string from the last commit
        """
        try:
            ignored_files: list[str] = [
                "package-lock.json",
                "yarn.lock",
                "poetry.lock",
                "pnpm-lock.yaml",
                "bun.lock",
            ]

            ignore_pattern: str = " ".join([f"':(exclude){f}'" for f in ignored_files])

            last_commit_diff: str = (
                await self.task.sandbox.run_command(
                    "cd /repo && git diff HEAD~1..HEAD -- {ignore_pattern}",
                )
            ).stdout

            git_diffs: str = self._format_diff(last_commit_diff)
            return git_diffs

        except Exception as e:
            logger.error(f"Error getting last commit diff: {e}")
            logger.error(traceback.format_exc())
            return "Error retrieving diff from last commit"

    async def create_pull_request(
        self, title: str, description: str, branch_name: str
    ) -> str:
        """
        Creates a pull request using the existing website push logic.

        :param commit_message: The title/message for the commit and PR
        :param commit_description: The description for the commit and PR
        :param branch_name: The branch name to create the PR from
        :return: The URL of the created pull request
        """
        if self.task.debug:
            logger.info(f"Debug mode: Would create PR '{title}' from {branch_name}")
            return "https://github.com/debug/repo/pull/1"

        try:
            logger.info(f"Creating pull request with message: {title}")

            original_branch_name: str = await self.task.settings.get_current_branch()

            pull_request: PullRequest = self.task.git.repo.create_pull(
                title=title,
                body=description,
                head=branch_name,
                base=original_branch_name,
            )
            await self.task.set_has_changes(False)
            logger.warning(f"Created PR: {pull_request.html_url}")
            logger.warning(f"PR number: {pull_request.number}")
            logger.info(pull_request)

            logger.info(f"Pull request created: {pull_request}")
            await self.task.task_state_manager.set_pr_task(pull_request.number)

            pr_url: str = (
                f"https://github.com/{self.repo.full_name}/pull/{pull_request.number}"
            )
            logger.info(f"Pull request created: {pr_url}")

            await self.task.chat.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(
                        message=f"I've created a pull request on your repository for branch {branch_name}: {pr_url}"
                    )
                ),
            )

            return WebsitePullRequest(
                branch_name=branch_name,
                pr_number=pull_request.number,
                pr_url=pr_url,
            )

        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}")
            logger.error(traceback.format_exc())
            raise
