import { Workspace, WorkspaceSettings } from "@/app/types/repos";
import { Workflow, WorkflowState } from "@/app/types/workflow";
import { ChatMessage, ChatMessageRole } from "@ctypes/chat-message";
import {
  FileSystem,
  LoadingTaskState,
  Task,
  TaskState,
  UIState,
} from "@ctypes/task";
import { create } from "zustand";

interface TaskStore {
  task: Task;
  workflow: Workflow;
  updateTask: (taskProps: Partial<Task>) => void;
  updateWorkflow: (workflowProps: Partial<Workflow>) => void;
  updateFileSystem: (fileSystemProps: Partial<FileSystem>) => void;
  updateUIState: (uiStateProps: Partial<UIState>) => void;
  setCurrentWorkspace: (space: Workspace | null) => void;
  updateCurrentWorkspace: (spaceProps: Partial<Workspace>) => void;
  addNewMessage: (newMessage: ChatMessage) => void;
  updateLastChatMessage: (messageProps: Partial<ChatMessage>) => void;
  updateCurrentWorkflow: (workflowProps: Partial<Workflow>) => void;
  setWorkspaceSettings: (settings: WorkspaceSettings | null) => void;
  updateWorkspaceSettings: (settings: Partial<WorkspaceSettings>) => void;
  setIsWorkspaceSettingsModalOpen: (open: boolean) => void;
}

const useTaskStore = create<TaskStore>((set, get) => ({
  task: {
    taskId: "",

    chatMessages: [],
    currentWorkspace: null,
    currentWorkflow: {
      workflowState: WorkflowState.IDLE,
    },
    isInSettingsAgent: false,

    fileSystem: {
      originalFileContents: {},
      editedFileContents: {},
    },
    uiState: {
      loadingTaskState: LoadingTaskState.LOADING,
      workspacePanelToShow: null,
      planPanelToShow: null,
      terminalShown: false,
      activeEditorFile: null,
      gitPanelActive: false,
      isWorkspaceSettingsModalOpen: false,
      workspaceSettingsPanelToShow: "settings",
      activeTab: null,
      sidebarExpanded: false,
      unreadMessages: false,
    },

    taskState: TaskState.IDLE,
  },

  workflow: {
    workflowState: WorkflowState.IDLE,
  },

  updateTask: (taskProps: Partial<Task>) =>
    set((state) => {
      // Deep merge for nested objects
      const newTask = {
        ...state.task,
        ...taskProps,
        // Special handling for nested objects
        currentWorkflow: taskProps.currentWorkflow
          ? {
              ...state.task.currentWorkflow,
              ...taskProps.currentWorkflow,
            }
          : state.task.currentWorkflow,
      };
      return { task: newTask };
    }),

  updateWorkflow: (workflowProps: Partial<Workflow>) =>
    set((state) => ({ workflow: { ...state.workflow, ...workflowProps } })),

  updateFileSystem: (fileSystemProps: Partial<FileSystem>) =>
    set((state) => ({
      task: {
        ...state.task,
        fileSystem: { ...state.task.fileSystem, ...fileSystemProps },
      },
    })),

  updateUIState: (uiStateProps: Partial<UIState>) =>
    set((state) => ({
      task: {
        ...state.task,
        uiState: { ...state.task.uiState, ...uiStateProps },
      },
    })),

  setCurrentWorkspace: (space: Workspace | null) =>
    set((state) => ({ task: { ...state.task, currentWorkspace: space } })),

  updateCurrentWorkspace: (spaceProps: Partial<Workspace>) =>
    set((state) => ({
      task: {
        ...state.task,
        currentWorkspace: state.task.currentWorkspace
          ? { ...state.task.currentWorkspace, ...spaceProps }
          : null,
      },
    })),

  addNewMessage: (newMessage: ChatMessage) =>
    set((state) => ({
      task: {
        ...state.task,
        chatMessages: [...state.task.chatMessages, newMessage],
        uiState: {
          ...state.task.uiState,
          unreadMessages:
            newMessage.role === ChatMessageRole.ASSISTANT
              ? true
              : state.task.uiState.unreadMessages,
        },
      },
    })),

  updateLastChatMessage: (messageProps: Partial<ChatMessage>) =>
    set((state) => ({
      task: {
        ...state.task,
        chatMessages: state.task.chatMessages.map((msg, index) =>
          index === state.task.chatMessages.length - 1
            ? { ...msg, ...messageProps }
            : msg,
        ),
      },
    })),

  updateCurrentWorkflow: (workflowProps: Partial<Workflow>) =>
    set((state) => ({
      task: {
        ...state.task,
        currentWorkflow: state.task.currentWorkflow
          ? { ...state.task.currentWorkflow, ...workflowProps }
          : { workflowState: WorkflowState.IDLE, ...workflowProps },
      },
    })),
  setWorkspaceSettings: (settings: WorkspaceSettings | null) =>
    set((state) => ({
      task: {
        ...state.task,
        currentWorkspace: state.task.currentWorkspace
          ? { ...state.task.currentWorkspace, settings }
          : null,
      },
    })),

  updateWorkspaceSettings: (settings: Partial<WorkspaceSettings>) =>
    set((state) => ({
      task: {
        ...state.task,
        currentWorkspace: state.task.currentWorkspace
          ? {
              ...state.task.currentWorkspace,
              settings: state.task.currentWorkspace.settings
                ? { ...state.task.currentWorkspace.settings, ...settings }
                : (settings as WorkspaceSettings),
            }
          : null,
      },
    })),

  setIsWorkspaceSettingsModalOpen: (open: boolean) =>
    set((state) => ({
      task: {
        ...state.task,
        isWorkspaceSettingsModalOpen: open,
        workspaceSettingsPanelToShow: "settings",
      },
    })),
}));

export const resetTask = () => {
  useTaskStore.setState({
    task: {
      taskId: "",

      chatMessages: [],
      currentWorkspace: null,
      currentWorkflow: {
        workflowState: WorkflowState.IDLE,
      },
      isInSettingsAgent: false,

      fileSystem: {
        originalFileContents: {},
        editedFileContents: {},
      },
      uiState: {
        loadingTaskState: LoadingTaskState.LOADING,
        workspacePanelToShow: null,
        planPanelToShow: null,
        terminalShown: false,
        activeEditorFile: null,
        gitPanelActive: false,
        isWorkspaceSettingsModalOpen: false,
        workspaceSettingsPanelToShow: "settings",
        activeTab: null,
        sidebarExpanded: false,
        unreadMessages: false,
      },

      taskState: TaskState.IDLE,
    },
  });
};

export { useTaskStore };
