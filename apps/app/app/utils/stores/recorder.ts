import { Recording } from "@/app/types/recording";
import { create } from "zustand";

export enum RecorderUIState {
  DEFAULT = "DEFAULT",
  RECORDING = "RECORDING",
  RECORDING_STOPPED = "RECORDING_STOPPED",
  REPLAYING = "REPLAYING",
  LOADED_RECORDING = "LOADED_RECORDING",
  SCREENSHOT = "SCREENSHOT",
  COMPONENT_SELECTION = "COMPONENT_SELECTION",
  FORCED_SCREENSHOT = "FORCED_SCREENSHOT",
}

interface RecorderState {
  isRecording: boolean;
  isReplaying: boolean;
  activeRecording: Recording | null;
  currentActionIndex: number;
  replayProgress: number;
  uiState: RecorderUIState;
  showInfoPanel: boolean;

  setIsRecording: (isRecording: boolean) => void;
  setIsReplaying: (isReplaying: boolean) => void;
  setActiveRecording: (recording: Recording | null) => void;
  setCurrentActionIndex: (index: number) => void;
  setReplayProgress: (progress: number) => void;
  setUIState: (state: RecorderUIState) => void;
  setShowInfoPanel: (show: boolean) => void;
  resetRecorder: () => void;
}

export const useRecorderStore = create<RecorderState>((set) => ({
  isRecording: false,
  isReplaying: false,
  activeRecording: null,
  currentActionIndex: -1,
  replayProgress: 0,
  uiState: RecorderUIState.DEFAULT,
  showInfoPanel: false,

  setIsRecording: (isRecording) => set({ isRecording }),
  setIsReplaying: (isReplaying) => set({ isReplaying }),
  setActiveRecording: (recording) => set({ activeRecording: recording }),
  setCurrentActionIndex: (index) => set({ currentActionIndex: index }),
  setReplayProgress: (progress) => set({ replayProgress: progress }),
  setUIState: (state) => set({ uiState: state }),
  setShowInfoPanel: (show) => set({ showInfoPanel: show }),

  resetRecorder: () =>
    set({
      isRecording: false,
      isReplaying: false,
      activeRecording: null,
      currentActionIndex: -1,
      replayProgress: 0,
      uiState: RecorderUIState.DEFAULT,
      showInfoPanel: false,
    }),
}));
