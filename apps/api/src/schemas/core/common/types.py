from enum import IntEnum, StrEnum


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    SUCCESS = "success"


class TaskState(StrEnum):
    IDLE = "idle"
    RECORDING_SENT = "recording_sent"
    RECORDING_RECEIVED = "recording_received"
    REPLAYING_RECORDING = "replaying_recording"
    GENERATING_BUG_REPORT = "generating_bug_report"
    BUG_REPORT_GENERATED = "bug_report_generated"
    ISSUE_CREATION_STARTED = "issue_creation_started"
    IMPLEMENTING = "implementing"
    VALIDATING = "validating"
    PR_CREATED = "pr_created"


class WorkflowState(StrEnum):
    RECORDING_SENT = "recording_sent"
    RECORDING_RECEIVED = "recording_received"
    GENERATING_BUG_REPORT = "generating_bug_report"
    BUG_REPORT_GENERATED = "bug_report_generated"
    ISSUE_CREATION_STARTED = "issue_creation_started"
    ISSUE_CREATED = "issue_created"

    # OLD
    CHAT_SENT = "chat_sent"
    CHAT_RECIEVED = "chat_received"
    ASKING_QUESTION = "question_asked"
    CREATING_NEW_PROMPT = "creating_new_prompt"
    SEARCHING_CODE = "searching_code"
    WRITING_PLAN = "writing_plan"
    IMPLEMENTING_PLAN = "implementing_plan"
    VALIDATING_CHANGES = "validating_changes"
    FIXING_RUNTIME = "fixing_runtime"
    DONE = "done"


# TODO: Implement this
class LoadingTaskState(IntEnum):
    LOADING = (0,)
    ALLOCATING = (1,)
    CLONING_REPO = (2,)
    INSTALLING_DEPS = (3,)
    INDEXING = (4,)
    BUILDING = (5,)
    SUCCESS = (6,)
    ERROR = (-1,)


# TODO: Refactor the *TaskState.BUILDING (frontend/backend unified type)
class MessageType(StrEnum):
    # Initialization
    ALLOCATING = "allocating"
    INITIALIZING_SANDBOX = "initializing_sandbox"
    CLONING_REPO = "cloning_repo"
    INSTALLING_DEPS = "installing_deps"
    LOADING_STATE_INDEXING = "loading_state_indexing"
    BUILDING = "building"
    INITIALIZATION_SUCCESS = "initialization_success"
    INITIALIZATION_ERROR = "initialization_error"

    # Terminal/fs
    RUN_COMMAND = "run_command"  # Request app to execute command
    MODIFY_FILE = "modify_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    HAS_CHANGES = "has_changes"

    # UI Commands
    OPEN_CHAT_PANEL = "open_chat_panel"
    SHOW_EDITOR = "show_editor"
    SHOW_WORKSPACE = "show_workspace"
    SHOW_BUG_REPORT = "show_bug_report"
    EXPAND_SIDEBAR = "expand_sidebar"
    SHOW_ISSUE = "show_issue"
    SHOW_TERMINAL = "show_terminal"  # Show terminal frontend
    HIDE_TERMINAL = "hide_terminal"  # Hide terminal frontend
    SHOW_GIT_PANEL = "show_git_panel"  # Show git panel frontend
    SHOW_SETTINGS_PANEL = "show_settings_panel"  # Show settings panel frontend
    SHOW_ENV_FILES_PANEL = "show_env_files_panel"  # Show env files panel frontend
    REFRESH_PAGE = "refresh_page"  # Refresh page frontend
    PLACEHOLDER_TASKS = "placeholder_tasks"  # Placeholder tasks for chat
    DISPLAY_PLAN = "display_plan"  # Display plan to frontend
    RECORDER_PROGRESS = "recorder_progress"  # Send recorder progress to frontend

    # Outputs
    USER_COMMAND = "user_command"  # Send user command to frontend
    TERMINAL_OUTPUT = "terminal_output"  # Send terminal output to frontend

    REQUESTING_BUTTONS = "requesting_buttons"  # Request app to send buttons to agent
    REQUEST_QUESTIONS = "request_questions"  # Request app to send questions to agent
    RESTART_WEBSITE = "restart_website"  # Request app to restart the website
    REQUEST_RUNTIME_FILES = (
        "request_runtime_files"  # Request app to get the runtime files
    )
    REQUEST_SETTINGS = "request_settings"  # Request app to get the settings

    # Events
    STATE_UPDATE = "state_update"  # Update state of agent
    SYNC_EVENT = "sync_event"  # Sync event with frontend
    WORKFLOW_RUNNING = (
        "workflow_running"  # Update state of task (if any workflow is running)
    )
    TASK_DETAILS = "task_details"  # Send task details to agent
    BUG_REPORT_CONTENTS = "bug_report_contents"  # Send bug report contents to agent
    BUG_REPORT_CONTENTS_PARTIAL = "bug_report_contents_partial"  # Partial contents
    ISSUE_CONTENTS = "issue_contents"  # Send issue contents to agent

    # Context
    NEW_PROMPT_GENERATED = (
        "new_prompt_generated"  # Send new prompt and summary to agent
    )

    ## Planning
    FILE_SEARCH_RESULTS = "file_search_results"  # Send file search results to agent
    PLAN_GENERATED = "plan_generated"  # Send refined plan to agent

    # Modifications
    MODIFICATION_PERFORMED = "modification_performed"  # Send modification to agent

    ## Validation
    DETERMINING_NEXT_STEP = "determining_next_step"
    COLLECTING_CONTEXT = "collecting_context"
    ATTEMPTING_FIX = "attempting_fix"
    DEBUG_STEP_PERFORMED = "debug-_step_performed"
    ACTION_HISTORY = "action_history"

    # Original File Contents
    ORIGINAL_FILE_CONTENTS = (
        "original_file_contents"  # Send list of files changed to agent
    )

    # Sandbox
    SET_PREVIEW_URL = "set_preview_url"  # Send sandbox IP to app

    # Chat
    CHAT_MESSAGE = "chat_message"  # Send chat message to frontend

    # Errors
    ERROR = "error"  # Send error to frontend
