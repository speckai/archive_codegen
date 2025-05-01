from enum import StrEnum


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    SUCCESS = "success"


class TaskState(StrEnum):
    CHAT_SENT = "chat_sent"
    CHAT_RECIEVED = "chat_received"
    ASKING_QUESTION = "question_asked"
    CREATING_NEW_PROMPT = "creating_new_prompt"
    SEARCHING_CODE = "searching_code"
    WRITING_PLAN = "writing_plan"
    IMPLEMENTING_PLAN = "implementing_plan"
    BUILDING = "building"
    FIXING_BUILD = "fixing_build"
    FIXING_RUNTIME = "fixing_runtime"
    DONE = "done"


class MessageType(StrEnum):
    # Initialization
    INITIALIZING = "initializing"
    INITIALIZATION_SUCCESS = "initialization_success"
    INITIALIZATION_ERROR = "initialization_error"

    # Terminal/fs
    RUN_COMMAND = "run_command"  # Request app to execute command
    MODIFY_FILE = "modify_file"
    CREATE_FILE = "create_file"

    # Outputs
    USER_COMMAND = "user_command"  # Send user command to frontend
    TERMINAL_OUTPUT = "terminal_output"  # Send terminal output to frontend
    SHOW_TERMINAL = "show_terminal"  # Show terminal frontend
    HIDE_TERMINAL = "hide_terminal"  # Hide terminal frontend

    REQUEST_QUESTIONS = "request_questions"  # Request app to send questions to agent
    RESTART_WEBSITE = "restart_website"  # Request app to restart the website

    # Events
    STATE_UPDATE = "state_update"  # Update state of agent
    SYNC_EVENT = "sync_event"  # Sync event with frontend

    ## Context
    NEW_PROMPT_GENERATED = (
        "new_prompt_generated"  # Send new prompt and summary to agent
    )

    ## Planning
    FILE_SEARCH_RESULTS = "file_search_results"  # Send file search results to agent
    PLAN_GENERATED = "plan_generated"  # Send refined plan to agent

    ## Modifications
    MODIFICATION_PERFORMED = "modification_performed"  # Send modification to agent

    ## Build
    BUILD_FIX_ATTEMPT = "build_fix_attempt"  # Send progress of build fix attempt

    ## Files Changed
    FILES_CHANGED = "files_changed"  # Send list of files changed to agent

    ## Sandbox
    SET_PREVIEW_URL = "set_preview_url"  # Send sandbox IP to app

    CHAT_MESSAGE = "chat_message"  # Send chat message to frontend
