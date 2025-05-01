from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from src.schemas.core.common.recordings import Recording
from src.utils.prompt_utils import format_prompt


class ChatMessageRole(StrEnum):
    ASSISTANT = "assistant"
    USER = "user"


class ButtonAction(StrEnum):
    YES_NO = "yes_no"
    OPEN_GIT_PANEL = "open_git_panel"
    OPEN_SETTINGS_PANEL = "open_settings_panel"
    ADD_PAGE_TO_CONTEXT = "add_page_to_context"
    SELECT_COMPONENTS = "select_components"
    OPEN_ENV_FILES_PANEL = "open_env_files_panel"


class GitCommitMessage(BaseModel):
    commit_hash: str
    commit_message: str
    unix_timestamp: int

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <git_commit_message>
            <commit_hash>
            {self.commit_hash}
            </commit_hash>
            <commit_message>
            {self.commit_message}
            </commit_message>
            </git_commit_message>
            """
        )


class Button(BaseModel):
    label: str
    value: Any | None = None
    action: ButtonAction | None = None
    clicked: bool | None = None

    @property
    def xml(self) -> str:  # TODO: Factor in clicked into here
        return format_prompt(
            f"""
            <button>
            <label>
            {self.label}
            </label>
            <value>
            {self.value}
            </value>
            <action>
            {self.action}
            </action>
            </button>
            """
        )


class Question(BaseModel):
    question: str
    answer: str | None = None

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <answered_question>
            <question>
            {self.question}
            </question>
            <answer>
            {self.answer or "Not answered yet"}
            </answer>
            </answered_question>
            """
        )


class KeyValuePair(BaseModel):
    key: str
    value: str

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <key_value_pair>
            <key>
            {self.key}
            </key>
            <value>
            {self.value}
            </value>
            </key_value_pair>
            """
        )


class MessageAttachments(BaseModel):
    key_value_pairs: list[KeyValuePair] | None = None
    buttons: list[Button] | None = None
    git_commit_message: GitCommitMessage | None = None
    recordings: list[Recording] | None = None

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <message_attachments>
            <key_value_pairs>
            {"\n".join([key_value_pair.xml for key_value_pair in self.key_value_pairs]) if self.key_value_pairs else ""}
            </key_value_pairs>
            <buttons>
            {"\n".join([button.xml for button in self.buttons]) if self.buttons else ""}
            </buttons>
            <git_commit_message>
            {self.git_commit_message.xml if self.git_commit_message else ""}
            </git_commit_message>
            </message_attachments>
            """
        )


class MainMessage(BaseModel):
    message: str
    is_italic: bool | None = None

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <main_message>
            {self.message}
            </main_message>
            """
        )


class MessageData(BaseModel):
    main_message: MainMessage | None = None
    questions: list[Question] | None = None
    attachments: MessageAttachments | None = None

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
            <message_data>
            <main_message>
            {self.main_message.xml if self.main_message else ""}
            </main_message>
            <questions>
            {"\n".join([question.xml for question in self.questions]) if self.questions else ""}
            </questions>
            <attachments>
            {self.attachments.xml if self.attachments else ""}
            </attachments>
            </message_data>
            """
        )


class ChatMessage(BaseModel):
    role: ChatMessageRole
    message_data: MessageData

    @property
    def xml(self) -> str:
        return format_prompt(
            f"""
        <{self.role}>
        {self.message_data.xml}
        </{self.role}>
        """
        )

    def indexed_xml(self, idx: int) -> str:
        return format_prompt(
            f"""
            <message_{idx}>
            <sender>
            {self.role}
            </sender>
            <message_data_dump>
            {self.message_data.xml}
            </message_data_dump>
            </message_{idx}>
            """
        )
