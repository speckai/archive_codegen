import { Image } from "./image";
import { Recording } from "./recording";
export enum ChatMessageRole {
  ASSISTANT = "assistant",
  USER = "user",
}

export enum ButtonAction {
  YES_NO = "yes_no",
  OPEN_GIT_PANEL = "open_git_panel",
  OPEN_SETTINGS_PANEL = "open_settings_panel",
  ADD_PAGE_TO_CONTEXT = "add_page_to_context",
  SELECT_COMPONENTS = "select_components",
}

export interface GitCommitMessage {
  commitHash: string;
  commitMessage: string;
  unixTimestamp: number;
}

export interface Button {
  label: string;
  value?: string | null;
  action?: ButtonAction | null;
  clicked: boolean | null;
}

export interface Question {
  question: string;
  answer?: string | null;
}

export interface KeyValuePair {
  key: string;
  value: string;
}

export interface MessageAttachments {
  keyValuePairs?: KeyValuePair[] | null;
  buttons?: Button[] | null;
  images?: Image[] | null;
  gitCommitMessage?: GitCommitMessage | null;
  recordings?: Recording[] | null;
}

export interface MainMessage {
  message: string;
  isItalic?: boolean | null;
}

export interface MessageData {
  mainMessage?: MainMessage | null;
  questions?: Question[] | null;
  attachments?: MessageAttachments | null;
}

export interface ChatMessage {
  role: ChatMessageRole;
  messageData: MessageData;
}
