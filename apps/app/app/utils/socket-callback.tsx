import { LoadingTaskState, TaskState } from "@/app/types/task";
import { resetTask, useTaskStore } from "@/app/utils/stores/task";
import { BugReport, convertToCamelCase } from "@ctypes/bug-report";
import { ChatMessageRole } from "@ctypes/chat-message";
import { MessageType } from "@ctypes/socket-message";
import { Socket } from "socket.io-client";
import { LogType } from "../types/terminal";
import { convertToWorkspace } from "./functions/repos";
import { useConsoleStore } from "./stores/console";
import { useWebviewStore } from "./stores/website-preview";

const convertTaskState = (state: string): TaskState => {
  const stateMap: Record<string, TaskState> = {
    idle: TaskState.IDLE,
    recording_sent: TaskState.RECORDING_SENT,
    recording_received: TaskState.RECORDING_RECEIVED,
    replaying_recording: TaskState.REPLAYING_RECORDING,
    generating_bug_report: TaskState.GENERATING_BUG_REPORT,
    bug_report_generated: TaskState.BUG_REPORT_GENERATED,
    issue_creation_started: TaskState.ISSUE_CREATION_STARTED,
    implementing: TaskState.IMPLEMENTING,
    validating: TaskState.VALIDATING,
    pr_created: TaskState.PR_CREATED,

    done: TaskState.DONE,
  };

  if (!(state in stateMap)) {
    console.error(`Unknown state: ${state} -- defaulting to IDLE`);
  }

  return stateMap[state] || TaskState.IDLE;
};

export const createSocketCallback = (toast: Function) => {
  return async (
    socket: Socket | null,
    requestData: { message_type: string; data: any },
  ) => {
    const { message_type: messageType, data } = requestData;
    const { addNewMessage, updateTask, updateUIState } =
      useTaskStore.getState();
    const { previewWidth, setWebviewSettings } = useWebviewStore.getState();

    const loadingStateMap = {
      [MessageType.ALLOCATING]: LoadingTaskState.ALLOCATING,
      [MessageType.INSTALLING_DEPS]: LoadingTaskState.INSTALLING_DEPS,
      [MessageType.INITIALIZING_SANDBOX]: LoadingTaskState.INITIALIZING_SANDBOX,
      [MessageType.CLONING_REPO]: LoadingTaskState.CLONING_REPO,
      [MessageType.LOADING_STATE_INDEXING]: LoadingTaskState.INDEXING,
      [MessageType.BUILDING]: LoadingTaskState.BUILDING,
      [MessageType.INITIALIZATION_SUCCESS]: LoadingTaskState.SUCCESS,
      [MessageType.INITIALIZATION_ERROR]: LoadingTaskState.ERROR,
      [MessageType.ALREADY_CONNECTED]: LoadingTaskState.ALREADY_CONNECTED,
    };

    if (messageType in loadingStateMap) {
      updateUIState({
        loadingTaskState:
          loadingStateMap[messageType as keyof typeof loadingStateMap],
      });
    }

    if (messageType === MessageType.SET_PREVIEW_URL) {
      let { url } = data;
      const { setSandboxBaseUrl, setWebviewSettings, setUrl, rerenderIframe } =
        useWebviewStore.getState();
      url.endsWith("/") && (url = url.slice(0, -1));
      setSandboxBaseUrl(url);
      setUrl("/");
      rerenderIframe();
    }

    if (messageType === MessageType.FORCE_RECONNECTED) {
      toast({
        title: "Connected",
        description: "Your previous session has been moved to this tab",
        status: "success",
      });
    }

    // Terminal
    if (messageType === MessageType.USER_COMMAND) {
      const { command } = data;
      const { addOutput } = useConsoleStore.getState();
      addOutput({ line: command, logType: LogType.USER });
    }

    if (messageType === MessageType.TERMINAL_OUTPUT) {
      const { output, is_error: isError } = data;
      const { addOutput } = useConsoleStore.getState();
      addOutput({
        line: output,
        logType: isError ? LogType.ERROR : LogType.INFO,
      });
    }

    if (messageType === MessageType.SHOW_TERMINAL) {
      updateUIState({ terminalShown: true });
    }

    if (messageType === MessageType.HIDE_TERMINAL) {
      updateUIState({ terminalShown: false });
    }

    if (messageType === MessageType.SHOW_GIT_PANEL) {
      updateUIState({ gitPanelActive: true });
    }

    if (messageType === MessageType.SHOW_SETTINGS_PANEL) {
      updateUIState({
        isWorkspaceSettingsModalOpen: true,
        workspaceSettingsPanelToShow: "settings",
      });
    }

    if (messageType === MessageType.SHOW_ENV_FILES_PANEL) {
      updateUIState({
        isWorkspaceSettingsModalOpen: true,
        workspaceSettingsPanelToShow: "env",
      });
    }

    if (messageType === MessageType.SHOW_BUG_REPORT) {
      updateUIState({
        activeTab: "workspace",
        workspacePanelToShow: "plan",
        planPanelToShow: "bugReport",
        sidebarExpanded: true,
      });
    }

    if (messageType === MessageType.EXPAND_SIDEBAR) {
      updateUIState({ sidebarExpanded: true });
      if (previewWidth >= 30) {
        setWebviewSettings({ previewWidth: 30 });
      }
    }

    if (messageType === MessageType.OPEN_CHAT_PANEL) {
      updateUIState({
        sidebarExpanded: true,
        activeTab: "chat",
        unreadMessages: false,
      });
      if (previewWidth >= 30) {
        setWebviewSettings({ previewWidth: 30 });
      }
    }

    if (messageType === MessageType.BUG_REPORT_CONTENTS) {
      const { bug_report: bugReport } = data;
      const bugReportNormalized = convertToCamelCase<BugReport>(bugReport);
      updateTask({ bugReport: bugReportNormalized });
    }

    if (messageType === MessageType.BUG_REPORT_CONTENTS_PARTIAL) {
      const { contents } = data;
      updateTask({
        bugReport: {
          report: contents,
          assetUrls: {},
          textModels: {},
        },
      });
    }

    if (messageType === MessageType.RECORDER_PROGRESS) {
      const { index, total, type } = data;
      updateTask({
        recorderProgress: {
          index: index,
          total: total,
          type: type,
        },
      });
    }

    if (messageType === MessageType.REFRESH_PAGE) {
      const { rerenderIframe } = useWebviewStore.getState();
      rerenderIframe();
    }

    // Message types
    if (messageType === MessageType.TASK_STATE_UPDATE) {
      const { state } = data;
      const convertedState = convertTaskState(state);
      updateTask({ taskState: convertedState });
    }

    if (messageType === MessageType.CHAT_MESSAGE) {
      const { role, message_data: messageData } = data;

      const convertRoleToChatMessageRole = (role: string): ChatMessageRole => {
        return role === "assistant"
          ? ChatMessageRole.ASSISTANT
          : ChatMessageRole.USER;
      };

      addNewMessage({
        role: convertRoleToChatMessageRole(role),
        messageData: {
          mainMessage: {
            message: messageData.main_message?.message,
            isItalic: messageData.main_message?.is_italic,
          },
          questions: messageData.questions,
          attachments: {
            recordings: messageData.attachments?.recordings,
            buttons: messageData.attachments?.buttons,
            keyValuePairs: messageData.attachments?.key_value_pairs,
            gitCommitMessage: messageData.attachments?.git_commit_message && {
              commitHash:
                messageData.attachments.git_commit_message.commit_hash,
              commitMessage:
                messageData.attachments.git_commit_message.commit_message,
              unixTimestamp:
                messageData.attachments.git_commit_message.unix_timestamp,
            },
          },
        },
      });
    }

    if (messageType === MessageType.TASK_DETAILS) {
      const { task_id: taskId, workspace } = data;
      updateTask({ taskId, currentWorkspace: convertToWorkspace(workspace) });
    }

    if (messageType === MessageType.SYNC_EVENT) {
      updateUIState({ loadingTaskState: LoadingTaskState.LOADING });

      const {
        latest_task_state: latestTaskState,
        task_actions: taskActions,
        chat_messages: chatMessages,
      } = data;

      if (taskActions === undefined) {
        console.warn("No actions found in sync event");
        return;
      }

      resetTask();

      if (latestTaskState !== undefined && latestTaskState !== null) {
        updateTask({
          taskState: convertTaskState(latestTaskState),
        });
      }

      for (const action of taskActions) {
        createSocketCallback(toast)(socket, {
          message_type: action.message_type,
          data: action.data,
        });
      }

      for (const chatMessage of chatMessages) {
        createSocketCallback(toast)(socket, {
          message_type: MessageType.CHAT_MESSAGE,
          data: chatMessage,
        });
      }
    }

    if (messageType === MessageType.ERROR) {
      const { error } = data;
      console.error(`Received server error: ${error}`);
      addNewMessage({
        role: ChatMessageRole.ASSISTANT,
        messageData: {
          mainMessage: {
            message: "I encountered an error! Please refresh and try again.",
            isItalic: false,
          },
        },
      });

      toast({
        title: "Server",
        description: "Server encountered an error. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };
};
