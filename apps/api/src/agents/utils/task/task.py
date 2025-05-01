import re
import traceback
from typing import Type

import socketio
from pydantic import BaseModel
from src.agents.code_analyzer.code_analyzer_agent import CodeAnalyzerAgent
from src.agents.implementer.implementer_agent import ImplementerAgent
from src.agents.issue_creation.issue_creation_agent import (
    IssueCreationAgent,
)
from src.agents.recording_bug_report.recording_bug_report_agent import (
    RecordingBugReportAgent,
)
from src.agents.recording_bug_report.utils.asset_storage import AssetStorage
from src.agents.search.brute_search_agent import BruteSearchAgent
from src.agents.search.search_agent import SearchAgent
from src.agents.search.tree_agent import TreeAgent
from src.agents.utils.task.chat import Chat
from src.agents.utils.task.context import Context
from src.agents.utils.task.debug.common import Debug
from src.agents.utils.task.debug.sandbox import DebugSandbox
from src.agents.utils.task.debug.settings import DebugSettings
from src.agents.utils.task.debug.website import DebugWebsite
from src.agents.utils.task.git import Git
from src.agents.utils.task.initializer import Initializer
from src.agents.utils.task.interfaces.browsing.recorder_player import RecordingPlayer
from src.agents.utils.task.interfaces.file_system import FileSystem
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.agents.utils.task.interfaces.terminal import Terminal
from src.agents.utils.task.interfaces.ui_functions import UIFunctions
from src.agents.utils.task.interfaces.website import Website
from src.agents.utils.task.settings import Settings
from src.agents.utils.task.socket_listener import SocketListener, listener
from src.agents.utils.task.task_state_manager import TaskStateManager
from src.agents.utils.task.workflow import Workflow
from src.agents.validation.validation_agent import ValidationAgent
from src.agents.validation.visual.visual_tester import VisualTester
from src.config import DEV
from src.database import Workspace
from src.github.utils import create_issue
from src.redis_manager import RedisManager
from src.schemas.account import User
from src.schemas.core.common import (
    BugReport,
    Button,
    ChatMessage,
    ChatMessageRole,
    FileObject,
    MainMessage,
    MessageAttachments,
    MessageData,
    MessageType,
    Question,
    Recording,
    RecordingCollection,
    RunningTaskProgress,
    TaskState,
)
from src.schemas.core.validation.visual import VisualValidationResponse
from src.schemas.github import GitHubIssue
from src.socket_manager import get_socket
from src.utils.debug.session_replay import SessionRecorder
from src.utils.llm.handler import Model, chat
from src.utils.logging import logger
from src.utils.markdown_utils import enrich_console_logs, extract_title_and_content

if DEV:
    from src.utils.debug.jupyter_utils import init_debug

    init_debug()


class Task:
    """Manages the execution of a user's task within a workspace.

    This class handles interactions with various agents, services, and
    interfaces to perform actions like code analysis, implementation,
    testing, and communication with the user.
    """

    def __init__(
        self,
        user: User,
        task_id: str,
        git_repo_id: int,
        issue_number: int | None,
        workspace: Workspace,
        debug: Debug | None = None,
    ):
        self.workspace = workspace
        self.session_recorder = SessionRecorder()

        self.debug = debug
        self.user: User = user
        self.current_workflow: Workflow | None = None

        self.debug_actions: list[dict] = []

        # Session properties
        self.task_id: str = task_id
        self.has_changes: bool = False
        self.context: Context = Context()

        # Session components
        self.file_system: FileSystem = FileSystem(self)
        self.terminal: Terminal = Terminal(self)
        self.git: Git = Git(self, git_repo_id, workspace, issue_number)
        self.chat: Chat = Chat(self)
        self.initializer: Initializer = Initializer(self)
        self.ui_functions: UIFunctions = UIFunctions(self)

        # Initialize sandbox and website based on debug mode
        self.settings: Settings | DebugSettings | None = None
        self.sandbox: Sandbox | DebugSandbox | None = None
        self.website: Website | DebugWebsite | None = None
        self.code_analyzer_agent: CodeAnalyzerAgent | None = None
        self.asset_storage = AssetStorage(self)

        if not debug:
            self.settings = Settings(self)
            self.sandbox = Sandbox(self)
            self.website = Website(self)
        else:
            self.settings = debug.settings
            self.sandbox = DebugSandbox(debug, self)
            self.website = DebugWebsite(debug, self)

        # Chat stuff
        self.is_workflow_running: bool = False
        self.user_socket_id: str | None = None

        # History/sync stuff
        self.actions: list[dict[MessageType, dict]] = []
        self.task_state_manager: TaskStateManager = TaskStateManager(self)

        # Socket properties
        if not self.debug:  # Only initialize sockets for non-debug mode
            self.initialize_listeners()

        # Global agents
        self.validation_agent: ValidationAgent = None
        self.search_agent: SearchAgent = None
        self.tree_agent: TreeAgent = None
        self.brute_search_agent: BruteSearchAgent = None
        self.visual_tester: VisualTester = None

        # Temp: New project details
        self.implementer_agent: ImplementerAgent = None
        self.issue_creation_agent: IssueCreationAgent = None
        self.recording_bug_report_agent: RecordingBugReportAgent = (
            RecordingBugReportAgent(self)
        )
        self.player: RecordingPlayer = None

    async def generate_bug_report(self, recording: Recording) -> str:
        await self.set_workflow_running(True)
        self.context.recordings = RecordingCollection(recordings=[recording])
        await self.task_state_manager.update_task_progress(RunningTaskProgress.ACTIVE)

        logger.debug("Generating bug report")
        await self.task_state_manager.send_state_update(TaskState.RECORDING_RECEIVED)

        await self.ui_functions.show_bug_report_tab()

        bug_report_result: BugReport = (
            await self.recording_bug_report_agent.generate_bug_report(recording)
        )

        self.context.bug_report = bug_report_result
        await self.task_state_manager.start_new_task()

        await self.task_state_manager.send_state_update(TaskState.BUG_REPORT_GENERATED)
        await self.send_update_data(
            MessageType.BUG_REPORT_CONTENTS,
            {
                "bug_report": bug_report_result.model_dump(),
            },
        )
        await self.task_state_manager.update_task_progress(RunningTaskProgress.BLOCKED)

    async def create_issue(self, bug_report: BugReport) -> None:
        await self.task_state_manager.update_task_progress(RunningTaskProgress.ACTIVE)
        await self.task_state_manager.send_state_update(
            TaskState.ISSUE_CREATION_STARTED
        )
        await self.ui_functions.show_issue_tab()

        title, content = extract_title_and_content(bug_report.report)
        success: bool = await self.task_state_manager.update_task_summary(title)
        logger.debug(f"Updating task summary to ({title}) - {success}")

        content: str = await self._replace_webms_with_gifs(content)

        issue: GitHubIssue = await create_issue(
            repo_id=self.git.repo_id,
            title=title,
            body=enrich_console_logs(content, bug_report.text_models),
            user_id=self.user.id,
        )
        self.git.issue_number = issue.number

        await self.chat.add_message(
            ChatMessageRole.ASSISTANT,
            MessageData(
                main_message=MainMessage(message=f"Issue created: {issue.html_url}")
            ),
        )

        await self.task_state_manager.send_state_update(TaskState.IMPLEMENTING)

        await self.implementer_agent.implement_bug_report(bug_report)

        await self.task_state_manager.send_state_update(TaskState.VALIDATING)
        validation_response: VisualValidationResponse = (
            await self.visual_tester.validate_functionality()
        )

        test_cases: dict = {}
        if validation_response and validation_response.events:
            for idx, event in enumerate(validation_response.events):
                before_screenshot_url: str = await self.asset_storage.store_image(
                    event.before_screenshot.data_bytes,
                    f"before_{idx}.{event.before_screenshot.extension}",
                )
                after_screenshot_url: str = await self.asset_storage.store_image(
                    event.after_screenshot.data_bytes,
                    f"after_{idx}.{event.after_screenshot.extension}",
                )

                test_cases[f"Test Case {idx + 1}"] = {
                    "status": "Fixed" if event.success else "Not Fixed",
                    "rationale": event.rationale,
                    "before_screenshot": before_screenshot_url,
                    "after_screenshot": after_screenshot_url,
                }
            branch_name: str | None = await self.git.create_branch(issue.model_dump())
            if not branch_name:
                logger.warning("Failed to create branch")
                return

            success: bool = await self.git.commit_changes()
            if not success:
                logger.warning("Failed to commit changes")

            pr_items = await self.git.get_pr_title_and_body(
                test_cases=test_cases,
                bug_report_dict=bug_report.model_dump(),
                issue_dict=issue.model_dump(),
            )

            # TODO: be sure to remove the hardcode to main once we have to do branches off of new branches.
            await self.task_state_manager.send_state_update(TaskState.PR_CREATED)
            await self.git.create_pull_request(
                title=pr_items.title,
                description=pr_items.body,
                branch_name=branch_name,
            )
        else:
            logger.warning("No visual validation response received")
        await self.set_workflow_running(False)
        if not self.user_socket_id:
            await self.destroy()

    async def _replace_webms_with_gifs(self, markdown_content: str) -> str:
        """
        Replace webm video links in markdown content with gifs while preserving the original webm links.

        :param markdown_content: The markdown content containing webm video links
        :return: Updated markdown content with webm links replaced by gifs
        """
        webm_pattern: str = r"!\[(.*?)\]\((.*?\.webm)\)"

        async def replace_webm_with_gif(match: re.Match) -> str:
            description: str = match[1]
            webm_url: str = match[2]

            try:
                (
                    gif_url,
                    original_webm_url,
                ) = await self.asset_storage.convert_webm_to_gif(webm_url)

                return f"![{description}]({gif_url})\n\n[View original video]({original_webm_url})"
            except Exception as e:
                logger.error(f"Error converting webm to gif: {str(e)}")
                logger.error(traceback.format_exc())
                return match[0]

        matches: list[re.Match] = re.finditer(webm_pattern, markdown_content)
        updated_content: str = markdown_content

        for match in list(matches):
            replacement: str = await replace_webm_with_gif(match)
            start: int = match.start()
            end: int = match.end()
            updated_content = (
                updated_content[:start] + replacement + updated_content[end:]
            )

        return updated_content

    async def create_agent_task(
        self,
        user_message: str,
        relevant_chats: list[ChatMessage],
        recordings: RecordingCollection,
        fully_autonomous: bool = False,
        is_cloning_site: bool = False,
    ) -> bool:
        self.current_workflow = Workflow(
            task=self,
            user_message=user_message,
            recordings=recordings,
            relevant_chats=relevant_chats,
            fully_autonomous=fully_autonomous,
            is_cloning_site=is_cloning_site,
        )

        try:
            task_success: bool = await self.current_workflow.start_task()
            await self.task_state_manager.update_task_progress(
                RunningTaskProgress.COMPLETED
            )
            if not self.user_socket_id:
                await self.destroy()

            return task_success
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            await self.task_state_manager.update_task_progress(
                RunningTaskProgress.CANCELLED
            )
            await self.send_update_data(
                MessageType.ERROR,
                {"message": str(e)},
            )
            await self.chat.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(
                        message="I encountered an error and had to abandon the task, please try again."
                    )
                ),
            )

    async def set_workflow_running(self, running: bool):
        self.is_workflow_running = running
        await self.send_update_data(MessageType.WORKFLOW_RUNNING, {"running": running})

    async def llm_chat(
        self,
        model_type: Model,
        system: str,
        message: str | list[dict[str, str]],
        caller: str,
        response_model: BaseModel | Type[str] = str,
        stream: bool = False,
        **kwargs,
    ) -> BaseModel | str:
        """
        Makes a chat request to the LLM
        :param message: The message to send to the LLM, or a list of messages to send to the LLM
        :param caller: The name of the user making the request, i.e agent name or function using this
        :return: The response from the LLM
        """
        assert isinstance(
            message, (str, list)
        ), "Message must be a string or a list of dictionaries"

        task_name: str = (
            "chat_agent_debug"
            if self.debug
            else "chat_agent_dev" if DEV else "chat_agent"
        )
        user: User = self.user

        messages: list[dict[str, str]] = []
        if model_type in {
            Model.GEMINI_2_0_FLASH,
            Model.GEMINI_2_0_FLASH_LITE,
        } and isinstance(message, str):
            messages = [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        elif isinstance(message, str):
            messages: list[dict[str, str]] = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message,
                        }
                    ],
                }
            ]
        else:
            messages = message

        return await chat(
            model_type,
            system,
            messages,
            response_model,
            task_path=f"/{caller}",
            task_id=self.task_id,
            task_name=task_name,
            user=user,
            stream=stream,
            **kwargs,
        )

    async def stop_task(self):
        if self.current_workflow:
            await self.set_workflow_running(False)
            self.current_workflow.cancel()
            await self.chat.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(message="I'm stopping work on the task.")
                ),
            )

    async def destroy(self):
        from src.task_manager import TaskManager

        TaskManager.deregister_task(self.task_id)

        self.initializer.cancel()
        logger.info("Stopping workflow")
        await self.set_workflow_running(False)
        await RedisManager.delete_task_id(self.task_id)
        await RedisManager.remove_worker_for_user(self.user.id)

        if self.current_workflow:
            self.current_workflow.destroy()

        if self.website:
            await self.website.stop()
            logger.info("Website stopped")

        await self.sandbox.destroy()

        if self.current_workflow:
            del self.current_workflow

    def initialize_listeners(self):
        """
        Questions and Answers: {"questions": [...]} -> list[dict[str, str]]
        """
        self.questions_listener: SocketListener = SocketListener(
            task=self,
            event_name="submit_answers",
            message_type=MessageType.REQUEST_QUESTIONS,
        )

        self.buttons_listener: SocketListener = SocketListener(
            task=self,
            event_name="submit_button",
            message_type=MessageType.REQUESTING_BUTTONS,
        )

        self.runtime_files_listener: SocketListener = SocketListener(
            task=self,
            event_name="requested_runtime_files",
            message_type=MessageType.REQUEST_RUNTIME_FILES,
        )

        self.settings_listener: SocketListener = SocketListener(
            task=self,
            event_name="requested_settings",
            message_type=MessageType.REQUEST_SETTINGS,
        )

        """
        Restart Website: None -> None
        """
        self.restart_website_listener: SocketListener = SocketListener(
            task=self,
            event_name="restart_ack",
            message_type=MessageType.RESTART_WEBSITE,
        )

    async def send_update_data(self, message_type: MessageType, data: dict) -> None:
        if self.debug:
            if message_type == MessageType.CHAT_MESSAGE:
                # Extract and log the message content
                message = (
                    data.get("message_data", {})
                    .get("main_message", {})
                    .get("message", "")
                )
                logger.info(f"[DEBUG] Chat message: {message}")
            return

        sio: socketio.AsyncServer = get_socket()
        await sio.emit(
            "task_data",
            {
                "message_type": message_type.value,
                "data": data,
                "repo_id": self.git.repo_id,
            },
            room=self.task_id,
        )

        non_logged_types: list[MessageType] = [
            MessageType.SYNC_EVENT,
            MessageType.CHAT_MESSAGE,
            MessageType.REQUEST_RUNTIME_FILES,
            MessageType.REQUEST_SETTINGS,
            MessageType.BUG_REPORT_CONTENTS_PARTIAL,
        ]
        if message_type not in non_logged_types:
            self.actions.append({"message_type": message_type, "data": data})

        non_duplicate_types: list[MessageType] = [
            MessageType.SET_PREVIEW_URL,
            MessageType.ALLOCATING,
            MessageType.INITIALIZING_SANDBOX,
            MessageType.CLONING_REPO,
            MessageType.INSTALLING_DEPS,
            MessageType.LOADING_STATE_INDEXING,
            MessageType.BUILDING,
            MessageType.INITIALIZATION_SUCCESS,
            MessageType.INITIALIZATION_ERROR,
            MessageType.SHOW_EDITOR,
            MessageType.SHOW_WORKSPACE,
            MessageType.SHOW_TERMINAL,
            MessageType.HIDE_TERMINAL,
            MessageType.SHOW_GIT_PANEL,
            MessageType.REFRESH_PAGE,
            MessageType.PLACEHOLDER_TASKS,
        ]  # Only keep the last instance of these types
        if message_type in non_duplicate_types:
            self.actions = [
                action
                for action in self.actions
                if action["message_type"] != message_type
            ]
            self.actions.append({"message_type": message_type, "data": data})

        if message_type == MessageType.MODIFY_FILE:
            file_path: str = data.get("file_path")
            self.actions = [
                action
                for action in self.actions
                if action["message_type"] != MessageType.MODIFY_FILE
                or action["data"]["file_path"] != file_path
            ]
            self.actions.append({"message_type": message_type, "data": data})

        if message_type == MessageType.CREATE_FILE:
            file_path: str = data.get("file_path")
            self.actions = [
                action
                for action in self.actions
                if action["message_type"] != MessageType.CREATE_FILE
                or action["data"]["file_path"] != file_path
            ]
            self.actions.append({"message_type": message_type, "data": data})

    async def set_has_changes(self, has_changes: bool):
        self.has_changes = has_changes
        await self.send_update_data(
            MessageType.HAS_CHANGES, {"has_changes": has_changes}
        )

    @listener("task_data", MessageType.REQUESTING_BUTTONS)
    async def request_buttons(
        self, buttons: list[Button], main_message: str = None
    ) -> str:
        await self.chat.add_message(
            ChatMessageRole.ASSISTANT,
            MessageData(
                main_message=(
                    MainMessage(message=main_message) if main_message else None
                ),
                attachments=MessageAttachments(buttons=buttons),
            ),
        )
        data: dict = await self.buttons_listener.request_data(
            {"buttons": [btn.value for btn in buttons]}
        )

        button_clicked: str = data.get("button_clicked")

        # Update the button in the last message
        for message in self.chat.history[-1].message_data.attachments.buttons:
            message.clicked = message.value == button_clicked
        return data.get("button_clicked")

    @listener("task_data", MessageType.REQUEST_QUESTIONS)
    async def ask_questions(
        self, questions: list[str], main_message: str = None
    ) -> list[dict[str, str]]:
        await self.chat.add_message(
            ChatMessageRole.ASSISTANT,
            MessageData(
                main_message=(
                    MainMessage(message=main_message) if main_message else None
                ),
                questions=[
                    Question(question=question, answer=None) for question in questions
                ],
            ),
        )
        if self.debug:
            responses = [{"question": q, "answer": "you choose"} for q in questions]
        else:
            data: dict = await self.questions_listener.request_data(
                {"questions": questions}
            )
            responses: list[dict[str, str]] = data.get("questions_and_answers", [])

        response_dict: dict[str, str] = {
            response["question"]: response["answer"] for response in responses
        }

        for question in self.chat.history[-1].message_data.questions:
            if question.question in response_dict:
                question.answer = response_dict[question.question]

        await self.chat.add_message(
            ChatMessageRole.USER,
            MessageData(
                main_message=MainMessage(
                    message=f"Sent {len(responses)} answers", is_italic=True
                )
            ),
        )
        return responses

    @listener("task_data", MessageType.REQUEST_RUNTIME_FILES)
    async def get_runtime_files(self) -> list[FileObject]:
        data: dict = await self.runtime_files_listener.request_data({})

        files: list[FileObject] = [
            FileObject(file_path=file["name"], content=file["contents"])
            for file in data.get("files", [])
        ]
        return files

    @listener("task_data", MessageType.REQUEST_SETTINGS)
    async def get_settings(self) -> dict:
        data: dict = await self.settings_listener.request_data({})
        return data.get("settings", {})
