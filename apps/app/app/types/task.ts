import { BugReport } from "./bug-report";
import { ChatMessage } from "./chat-message";
import { Issue } from "./issue";
import { Workspace } from "./repos";
import { Workflow } from "./workflow";

export enum LoadingTaskState {
  LOADING = 0,
  ALLOCATING = 1,
  INITIALIZING_SANDBOX = 3,
  CLONING_REPO = 4,
  INSTALLING_DEPS = 5,
  INDEXING = 6,
  BUILDING = 7,
  SUCCESS = 8,
  ERROR = -1,
  ALREADY_CONNECTED = -2,
}

export enum TaskState {
  IDLE = 0,
  RECORDING_SENT = 1,
  RECORDING_RECEIVED = 2,
  REPLAYING_RECORDING = 3,
  GENERATING_BUG_REPORT = 4,
  BUG_REPORT_GENERATED = 5,
  BUG_REPORT_SUBMITTED = 6,
  ISSUE_CREATION_STARTED = 7,
  ISSUE_CREATED = 8,
  IMPLEMENTING = 9,
  VALIDATING = 10,
  PR_CREATED = 11,
  DONE = 12,
}

export interface UIState {
  loadingTaskState: LoadingTaskState;
  workspacePanelToShow: "workspace" | "editor" | "plan" | null;
  planPanelToShow: "bugReport" | null;
  terminalShown: boolean;
  activeEditorFile: string | null;
  gitPanelActive: boolean;
  isWorkspaceSettingsModalOpen: boolean;
  workspaceSettingsPanelToShow: "settings" | "env";
  activeTab: "chat" | "workspace" | null;
  sidebarExpanded: boolean;
  unreadMessages: boolean;
}

export interface FileSystem {
  // Files changed
  originalFileContents?: { [key: string]: string };

  // Edited files
  // key: file path, value: file contents
  editedFileContents?: { [key: string]: string };

  // Has changes
  hasChanges?: boolean;
}

export interface RecorderProgress {
  index: number;
  total: number;
  type: string;
}

export interface Task {
  taskId: string;

  chatMessages: ChatMessage[];
  currentWorkspace: Workspace | null;

  // Current workflow
  currentWorkflow: Workflow;

  isInSettingsAgent?: boolean;

  fileSystem: FileSystem;
  uiState: UIState;

  // MD stuff
  bugReport?: BugReport;
  issue?: Issue;

  taskState: TaskState;

  recorderProgress?: RecorderProgress;
}
