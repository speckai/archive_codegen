export enum MessageType {
  // Initialization
  ALREADY_CONNECTED = "already_connected",

  // Loading states
  ALLOCATING = "allocating",
  INITIALIZING_SANDBOX = "initializing_sandbox",
  CLONING_REPO = "cloning_repo",
  INSTALLING_DEPS = "installing_deps",
  LOADING_STATE_INDEXING = "loading_state_indexing",
  BUILDING = "building",
  INITIALIZATION_SUCCESS = "initialization_success",
  INITIALIZATION_ERROR = "initialization_error",

  // Command outputs
  USER_COMMAND = "user_command", // Send user command to agent
  TERMINAL_OUTPUT = "terminal_output", // Send terminal output to agent

  // UI functions
  SHOW_EDITOR = "show_editor", // Show editor
  SHOW_WORKSPACE = "show_workspace", // Show workspace
  SHOW_BUG_REPORT = "show_bug_report", // Show bug report
  EXPAND_SIDEBAR = "expand_sidebar", // Expand sidebar
  OPEN_CHAT_PANEL = "open_chat_panel", // Open chat panel and expand sidebar
  SHOW_ISSUE = "show_issue", // Show issue
  RECORDER_PROGRESS = "recorder_progress", // Send recorder progress to agent

  SHOW_TERMINAL = "show_terminal", // Show terminal
  HIDE_TERMINAL = "hide_terminal", // Hide terminal
  SHOW_GIT_PANEL = "show_git_panel", // Show git panel
  SHOW_SETTINGS_PANEL = "show_settings_panel", // Show settings panel
  SHOW_ENV_FILES_PANEL = "show_env_files_panel", // Show env files panel
  REFRESH_PAGE = "refresh_page", // Refresh page

  REQUEST_QUESTIONS = "request_questions", // Request app to send questions to agent
  REQUEST_RUNTIME_FILES = "request_runtime_files", // Request app to send runtime files to agent
  REQUEST_SETTINGS = "request_settings", // Request app to send settings to agent

  // Events
  TASK_STATE_UPDATE = "task_state_update", // Update state of agent
  SYNC_EVENT = "sync_event", // Send sync event to agent
  TASK_DETAILS = "task_details", // Send task details to agent
  BUG_REPORT_CONTENTS = "bug_report_contents", // Send bug report contents to agent
  BUG_REPORT_CONTENTS_PARTIAL = "bug_report_contents_partial", // Send partial bug report contents to agent
  ISSUE_CONTENTS = "issue_contents", // Send issue contents to agent

  // Modifications
  MODIFICATION_PERFORMED = "modification_performed", // Send modification to agent
  MODIFY_FILE = "modify_file",
  CREATE_FILE = "create_file",
  DELETE_FILE = "delete_file",
  HAS_CHANGES = "has_changes",

  // Validation
  DETERMINING_NEXT_STEP = "determining_next_step",
  COLLECTING_CONTEXT = "collecting_context",
  ATTEMPTING_FIX = "attempting_fix",
  DEBUG_STEP_PERFORMED = "debug_step_performed",
  ACTION_HISTORY = "action_history",

  // Files
  ORIGINAL_FILE_CONTENTS = "original_file_contents", // Send original file contents to agent

  // Website Preview
  SET_PREVIEW_URL = "set_preview_url", // Send sandbox IP to app

  // Chat
  CHAT_MESSAGE = "chat_message", // Echo chat message to app

  // Errors
  ERROR = "error",

  FORCE_RECONNECTED = "force_reconnected",
}
