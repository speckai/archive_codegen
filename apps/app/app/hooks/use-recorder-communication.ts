import { Recording } from "@/app/types/recording";
import { RecorderUIState, useRecorderStore } from "@/app/utils/stores/recorder";
import { useEffect } from "react";

type MessageHandler = (type: string, data: any) => void;

export function useRecorderCommunication(onMessage: MessageHandler) {
  const {
    setIsRecording,
    setIsReplaying,
    setActiveRecording,
    setCurrentActionIndex,
    setReplayProgress,
    setUIState,
    setShowInfoPanel,
    activeRecording,
  } = useRecorderStore();

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { type, data } = event.data;

      switch (type) {
        case "recording_state":
          if (data.events || data.consoleLogs) {
            setActiveRecording({
              ...(activeRecording || {}),
              events: data.events || [],
              consoleLogs: data.consoleLogs || [],
              duration: data.duration || 0,
            } as Recording);
            if (data.events?.length === 0) {
              setUIState(RecorderUIState.DEFAULT);
              setShowInfoPanel(false);
            }
          }
          if (typeof data.isRecording === "boolean") {
            setIsRecording(data.isRecording);
            if (data.isRecording) {
              setUIState(RecorderUIState.RECORDING);
            } else if (data.events && data.events.length > 0) {
              setUIState(RecorderUIState.RECORDING_STOPPED);
            }
          }
          break;
        case "recording_stopped":
          setIsRecording(false);
          setUIState(RecorderUIState.RECORDING_STOPPED);
          setShowInfoPanel(true);
          break;
        case "recording_discarded":
          setActiveRecording(null);
          setIsRecording(false);
          setUIState(RecorderUIState.DEFAULT);
          setShowInfoPanel(false);
          break;
        case "start_replay":
          setIsReplaying(true);
          setUIState(RecorderUIState.REPLAYING);
          setShowInfoPanel(true);
          setReplayProgress(0);
          break;
        case "replay_progress":
          setReplayProgress(data?.progress || 0);
          break;
        case "replay_action":
          setCurrentActionIndex(data);
          break;
        case "replay_finished":
          setIsReplaying(false);
          setUIState(
            activeRecording?.id
              ? RecorderUIState.LOADED_RECORDING
              : RecorderUIState.RECORDING_STOPPED,
          );
          setShowInfoPanel(true);
          setReplayProgress(0);
          setCurrentActionIndex(-1);

          break;
        case "request_recording_state":
          const iframe = document.getElementById(
            "speck-preview-iframe",
          ) as HTMLIFrameElement;
          if (iframe?.contentWindow && activeRecording) {
            iframe.contentWindow.postMessage(
              {
                type: "set_recording_data",
                data: {
                  events: activeRecording.events,
                  consoleLogs: activeRecording.consoleLogs,
                  initialUrl: activeRecording.initialUrl,
                  duration: activeRecording.duration,
                },
              },
              "*",
            );
          }
          break;
      }

      if (onMessage) {
        onMessage(type, data);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [
    setIsRecording,
    setIsReplaying,
    setActiveRecording,
    setCurrentActionIndex,
    setReplayProgress,
    setUIState,
    setShowInfoPanel,
    onMessage,
    activeRecording,
  ]);
}
