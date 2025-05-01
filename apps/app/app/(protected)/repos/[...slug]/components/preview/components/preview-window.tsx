"use client";

import { useRecorderCommunication } from "@/app/hooks/use-recorder-communication";
import { SelectedComponent } from "@/app/types/selected-components";
import { RecorderUIState, useRecorderStore } from "@/app/utils/stores/recorder";
import {
  Box,
  Button,
  HStack,
  Image,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { BsCamera } from "react-icons/bs";
import { FaReact } from "react-icons/fa";
import { FaVideo } from "react-icons/fa6";

import { TaskState } from "@/app/types/task";
import { useTaskStore } from "@/app/utils/stores/task";
import BaseModal from "./base-modal";
import Transcript from "./transcript/panel";

interface ClickAnimation {
  rect: {
    top: number;
    left: number;
    width: number;
    height: number;
  };
  id: string;
}

interface ClickAnimationData {
  rect: {
    top: number;
    left: number;
    width: number;
    height: number;
  };
}

const ConsoleLogMarker = ({ type }: { type: string }) => (
  <Box
    w="1px"
    h="100%"
    bg={type === "error" ? "red.500" : type === "warn" ? "yellow.500" : "white"}
    position="absolute"
    top={0}
    left={0}
  />
);

const AnnotationModal = ({
  isOpen,
  onClose,
  onSave,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (annotation: string) => void;
}) => {
  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      onSave={onSave}
      title="Annotate Recording"
      description="Add any extra details that might help Speck understand the issue better."
      textareaPlaceholder="Add any extra details that you think are relevant."
      cancelButtonText="Go Back"
      saveButtonText="Submit"
      requireAnnotation={false}
    />
  );
};

const ComponentAnnotationModal = ({
  isOpen,
  onClose,
  onSave,
  componentPreviewUrl,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (annotation: string) => void;
  componentPreviewUrl: string;
}) => {
  const content = componentPreviewUrl ? (
    <Box
      border="1px solid rgba(255, 255, 255, 0.1)"
      borderRadius="md"
      overflow="hidden"
      maxHeight="300px"
    >
      <Image
        src={componentPreviewUrl}
        alt="Component Preview"
        objectFit="contain"
        maxHeight="300px"
      />
    </Box>
  ) : null;

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      onSave={onSave}
      title="Annotate Component"
      content={content}
      textareaPlaceholder="Describe what changes need to be made to this component."
      requireAnnotation={true}
    />
  );
};

const ScreenshotAnnotationModal = ({
  isOpen,
  onClose,
  onSave,
  screenshotDataUrl,
  isForcedScreenshot = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSave: (annotation: string) => void;
  screenshotDataUrl: string;
  isForcedScreenshot?: boolean;
}) => {
  const content = (
    <HStack w="full" justifyContent="center" spacing={4}>
      <Image
        src={screenshotDataUrl}
        maxH="55vh"
        fit="contain"
        borderRadius="md"
        border="1px solid rgba(255, 255, 255, 0.1)"
      />
    </HStack>
  );

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      onSave={onSave}
      title={
        isForcedScreenshot ? "Stopping Recording..." : "Annotate Screenshot"
      }
      description={
        isForcedScreenshot
          ? "Your recording requires a final screenshot. Add an annotation to describe what you've demonstrated."
          : "Add an annotation to this screenshot."
      }
      content={content}
      textareaPlaceholder="Describe what's in the screenshot..."
      cancelButtonText={isForcedScreenshot ? "Discard Recording" : "Cancel"}
      saveButtonText={isForcedScreenshot ? "Save Recording" : "Save"}
      requireAnnotation={true}
    />
  );
};

export default function PreviewWindow() {
  const {
    isRecording,
    isReplaying,
    activeRecording,
    currentActionIndex,
    replayProgress,
    uiState,
    setIsRecording,
    setIsReplaying,
    setActiveRecording,
    setUIState,
    setShowInfoPanel,
    setReplayProgress,
  } = useRecorderStore();

  const { task } = useTaskStore();

  const [clickAnimations, setClickAnimations] = useState<ClickAnimation[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [pendingSaveRecording, setPendingSaveRecording] = useState<any>(null);

  const [screenshotDataUrl, setScreenshotDataUrl] = useState<string>("");
  const [showScreenshotModal, setShowScreenshotModal] = useState(false);
  const [isForcedScreenshot, setIsForcedScreenshot] = useState(false);
  const [componentPreviewUrl, setComponentPreviewUrl] = useState<string>("");
  const [showComponentModal, setShowComponentModal] = useState(false);
  const [selectedComponent, setSelectedComponent] =
    useState<SelectedComponent | null>(null);
  const [isScreenshotLoading, setIsScreenshotLoading] = useState(false);

  const actionsContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (
      actionsContainerRef.current &&
      currentActionIndex >= 0 &&
      activeRecording?.events
    ) {
      const actionElements = actionsContainerRef.current.querySelectorAll(
        "[data-action-index]",
      );

      const currentActionElement = Array.from(actionElements).find(
        (el) =>
          parseInt(el.getAttribute("data-action-index") || "-1") ===
          currentActionIndex,
      );

      if (currentActionElement) {
        currentActionElement.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }
    }
  }, [currentActionIndex, activeRecording]);

  const toggleComponentSelection = (enabled: boolean) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;

    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage(
        { type: "select_component", enabled },
        "*",
      );
    }
  };

  const handleMessage = (type: string, data: any) => {
    if (type === "click_animation") {
      const clickData = data as ClickAnimationData;
      const id = Math.random().toString(36).substring(2, 9);
      setClickAnimations((prev) => [...prev, { rect: clickData.rect, id }]);

      setTimeout(() => {
        setClickAnimations((prev) => prev.filter((anim) => anim.id !== id));
      }, 800);
    } else if (type === "component_selected") {
      const iframe = document.getElementById(
        "speck-preview-iframe",
      ) as HTMLIFrameElement;

      if (iframe?.contentWindow) {
        iframe.contentWindow.postMessage(
          { type: "take_component_screenshot" },
          "*",
        );
      }
      setSelectedComponent(data);
      setShowComponentModal(true);
    } else if (type === "component_screenshot_result") {
      setComponentPreviewUrl(data);
    } else if (type === "screenshot_result") {
      setScreenshotDataUrl(data);
      setShowScreenshotModal(true);
      setIsScreenshotLoading(false);
    } else if (type === "forced_screenshot_result") {
      setScreenshotDataUrl(data);
      setShowScreenshotModal(true);
      setIsForcedScreenshot(true);
      setIsScreenshotLoading(false);
    } else if (type === "require_screenshot") {
      setIsForcedScreenshot(true);
      setUIState(RecorderUIState.FORCED_SCREENSHOT);
      takeScreenshotInternal(true);
    } else if (type === "recording_data_with_screenshot") {
      setPendingSaveRecording(data.data);
      handleRecordingSave(data.annotation);
    } else if (type === "recording_discarded") {
      setIsRecording(false);
      setActiveRecording(null);
      setUIState(RecorderUIState.DEFAULT);
      setShowInfoPanel(false);
    } else if (type === "cancel") {
      toggleComponentSelection(false);
    } else if (type === "recording_data") {
      setPendingSaveRecording(data);
      setShowSaveDialog(true);
    }
  };

  useRecorderCommunication(handleMessage);

  useEffect(() => {
    if (
      activeRecording &&
      activeRecording.events &&
      activeRecording.events.length > 0 &&
      !isRecording
    ) {
      setShowInfoPanel(true);
      if (activeRecording.id) {
        setUIState(RecorderUIState.LOADED_RECORDING);
      }
    } else if (isRecording) {
      setShowInfoPanel(false);
    }
  }, [activeRecording, isRecording, setShowInfoPanel, setUIState]);

  const toggleRecording = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage({ type: "toggle_recording" }, "*");
      if (isRecording) {
        // When stopping a recording, set isRecording to false immediately
        // even though the recorder will still capture the final screenshot if needed
        setIsRecording(false);
        setUIState(RecorderUIState.RECORDING_STOPPED);
      } else {
        setIsRecording(true);
        setUIState(RecorderUIState.RECORDING);
        setShowInfoPanel(false);
        setActiveRecording(null);
      }
    }
  };

  const toggleReplay = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      if (isReplaying) {
        iframe.contentWindow.postMessage({ type: "stop_replay" }, "*");
        setIsReplaying(false);
        setUIState(
          activeRecording?.id
            ? RecorderUIState.LOADED_RECORDING
            : RecorderUIState.RECORDING_STOPPED,
        );
        setShowInfoPanel(true);
        setReplayProgress(0);
      } else if (activeRecording) {
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

        iframe.contentWindow.postMessage({ type: "request_replay" }, "*");
        setIsReplaying(true);
        setUIState(RecorderUIState.REPLAYING);
        setShowInfoPanel(true);
        setReplayProgress(0);
      }
    }
  };

  const saveRecording = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage(
        {
          type: "request_recording_data",
        },
        "*",
      );
    }
  };

  const handleRecordingSave = (annotation: string) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow && pendingSaveRecording) {
      iframe.contentWindow.postMessage(
        {
          type: "save_recording",
          data: { annotation },
        },
        "*",
      );
      setUIState(RecorderUIState.DEFAULT);
      setShowInfoPanel(false);
      setPendingSaveRecording(null);
    } else {
      console.warn("No iframe content window");
      console.warn("pendingSaveRecording", pendingSaveRecording);
    }
    setShowSaveDialog(false);
  };

  const handleRecordingCancel = () => {
    setPendingSaveRecording(null);
    setShowSaveDialog(false);
  };

  const discardRecording = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage({ type: "discard_recording" }, "*");
      setActiveRecording(null);
      setUIState(RecorderUIState.DEFAULT);
      setShowInfoPanel(false);
    }
  };

  const handleGoBack = () => {
    setActiveRecording(null);
    setUIState(RecorderUIState.DEFAULT);
    setShowInfoPanel(false);
  };

  const selectComponent = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;

    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage(
        { type: "select_component", enabled: true },
        "*",
      );
      setUIState(RecorderUIState.COMPONENT_SELECTION);
    }
  };

  const takeScreenshotInternal = (isForced = false) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;

    if (iframe?.contentWindow) {
      setIsScreenshotLoading(true);
      if (isForced) {
        iframe.contentWindow.postMessage(
          { type: "take_forced_screenshot" },
          "*",
        );
      } else {
        iframe.contentWindow.postMessage({ type: "take_screenshot" }, "*");
      }

      const previewWindow = document.querySelector("[data-preview-window]");
      if (previewWindow) {
        const flashElement = document.createElement("div");
        flashElement.style.position = "absolute";
        flashElement.style.top = "0";
        flashElement.style.left = "0";
        flashElement.style.width = "100%";
        flashElement.style.height = "100%";
        flashElement.style.backgroundColor = "white";
        flashElement.style.opacity = "0.4";
        flashElement.style.zIndex = "9999";
        flashElement.style.pointerEvents = "none";
        flashElement.style.transition = "opacity 0.6s ease-out";
        previewWindow.appendChild(flashElement);

        setTimeout(() => {
          flashElement.style.opacity = "0";
          setTimeout(() => {
            previewWindow.removeChild(flashElement);
          }, 600);
        }, 50);
      }
    }
  };

  const takeScreenshot = () => {
    takeScreenshotInternal(false);
  };

  const handleScreenshotSave = (annotation: string) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;

    if (iframe?.contentWindow) {
      if (isForcedScreenshot) {
        iframe.contentWindow.postMessage(
          {
            type: "save_forced_screenshot",
            data: {
              annotation,
              imageData: screenshotDataUrl,
            },
          },
          "*",
        );
        setIsForcedScreenshot(false);
        // The recording flow will continue from the iframe message handler
      } else {
        iframe.contentWindow.postMessage(
          {
            type: "save_screenshot",
            data: {
              annotation,
              imageData: screenshotDataUrl,
            },
          },
          "*",
        );
      }
    }
    setShowScreenshotModal(false);
    setUIState(RecorderUIState.RECORDING);
  };

  const handleScreenshotCancel = () => {
    setShowScreenshotModal(false);

    // If it was a forced screenshot and the user cancels, discard the recording
    if (isForcedScreenshot) {
      const iframe = document.getElementById(
        "speck-preview-iframe",
      ) as HTMLIFrameElement;

      if (iframe?.contentWindow) {
        iframe.contentWindow.postMessage(
          { type: "cancel_forced_screenshot" },
          "*",
        );
      }
      setIsForcedScreenshot(false);
      setUIState(RecorderUIState.DEFAULT);
      // Already set in the new toggleRecording function
      // setIsRecording(false);
    } else {
      setUIState(RecorderUIState.RECORDING);
    }
  };

  const handleComponentSave = (annotation: string) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;

    if (iframe?.contentWindow && selectedComponent) {
      iframe.contentWindow.postMessage(
        {
          type: "save_component_selection",
          data: {
            component: selectedComponent,
            annotation,
            imageData: componentPreviewUrl,
          },
        },
        "*",
      );
    }
    setShowComponentModal(false);
    setSelectedComponent(null);

    setUIState(RecorderUIState.RECORDING);
  };

  const cancelSelectComponent = () => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage(
        { type: "select_component", enabled: false },
        "*",
      );
    }
    setUIState(RecorderUIState.RECORDING);
  };

  const renderControlPill = () => {
    switch (uiState) {
      case RecorderUIState.DEFAULT:
        return (
          <motion.div layout key="default">
            <HStack spacing={0} justifyContent="center">
              <Button
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={toggleRecording}
                leftIcon={<FaVideo />}
                borderRadius="full"
              >
                Record
              </Button>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.RECORDING:
        return (
          <motion.div layout key="recording">
            <HStack spacing={0} justifyContent="center">
              <Button
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={toggleRecording}
                borderLeftRadius="full"
                borderRightRadius="0"
              >
                <Box
                  w="8px"
                  h="8px"
                  borderRadius="full"
                  bg="red.500"
                  animation="pulse 1s infinite"
                  mr={2}
                />
                Stop
              </Button>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="blue"
                variant="ghost"
                onClick={selectComponent}
                borderRadius="0"
                leftIcon={<FaReact />}
              >
                Select Element
              </Button>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="teal"
                variant="ghost"
                onClick={takeScreenshot}
                borderLeftRadius="0"
                borderRightRadius="full"
                leftIcon={<BsCamera />}
                isLoading={isScreenshotLoading}
              >
                Screenshot
              </Button>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.COMPONENT_SELECTION:
        return (
          <motion.div layout key="component-selection">
            <HStack spacing={0} justifyContent="center">
              <Box
                w="8px"
                h="8px"
                borderRadius="full"
                bg="blue.500"
                animation="pulse 1s infinite"
                ml={3}
                mr={2}
              />
              <Text color="white" fontSize="sm" mr={2}>
                Select an element
              </Text>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={cancelSelectComponent}
                borderRightRadius="full"
              >
                Cancel
              </Button>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.FORCED_SCREENSHOT:
        return (
          <motion.div layout key="forced-screenshot">
            <HStack spacing={0} justifyContent="center">
              <Box
                w="8px"
                h="8px"
                borderRadius="full"
                bg="red.500"
                animation="pulse 1s infinite"
                ml={3}
                mr={2}
              />
              <Text color="white" fontSize="sm" mr={2}>
                Stopping recording...
              </Text>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.RECORDING_STOPPED:
        return (
          <motion.div layout key="recording-stopped">
            <HStack spacing={0} justifyContent="center">
              <Box
                w="8px"
                h="8px"
                borderRadius="full"
                bg="red.500"
                ml={3}
                mr={2}
              />
              <Button
                size="sm"
                colorScheme="green"
                variant="ghost"
                onClick={saveRecording}
                borderRadius="0"
              >
                Submit
              </Button>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="red"
                variant="ghost"
                onClick={discardRecording}
                borderRadius="0"
              >
                Discard
              </Button>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="blue"
                variant="ghost"
                onClick={toggleReplay}
                borderRightRadius="full"
              >
                Replay
              </Button>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.LOADED_RECORDING:
        return (
          <motion.div layout key="loaded-recording">
            <HStack spacing={0} justifyContent="center">
              <Button
                size="sm"
                colorScheme="blue"
                variant="ghost"
                onClick={toggleReplay}
                borderLeftRadius="full"
                px={4}
              >
                {isReplaying ? "Stop" : "Replay"}
              </Button>
              <Box w="1px" h="15px" bg="rgba(255, 255, 255, 0.2)" />
              <Button
                size="sm"
                colorScheme="gray"
                variant="ghost"
                onClick={handleGoBack}
                borderRightRadius="full"
                px={4}
              >
                Back
              </Button>
            </HStack>
          </motion.div>
        );

      case RecorderUIState.REPLAYING:
        return (
          <motion.div layout key="replaying">
            <VStack spacing={2} align="center" w="300px">
              <Box
                bg="rgba(20, 20, 20, 0.4)"
                backdropFilter="blur(10px)"
                borderRadius="full"
                border="1px solid rgba(255, 255, 255, 0.1)"
                p={2}
                pointerEvents="auto"
                width="100%"
              >
                <Box
                  position="relative"
                  w="100%"
                  h="3px"
                  bg="rgba(255, 255, 255, 0.2)"
                  borderRadius="full"
                  overflow="hidden"
                >
                  <Box
                    h="100%"
                    w={`${replayProgress}%`}
                    bg="blue.500"
                    transition="width 0.3s ease"
                  />
                  {activeRecording?.consoleLogs.map((log, index) => (
                    <ConsoleLogMarker key={index} type={log.level} />
                  ))}
                </Box>
              </Box>
            </VStack>
          </motion.div>
        );

      default:
        return null;
    }
  };

  return (
    <>
      <AnnotationModal
        isOpen={showSaveDialog}
        onClose={handleRecordingCancel}
        onSave={handleRecordingSave}
      />
      <ScreenshotAnnotationModal
        isOpen={showScreenshotModal}
        onClose={handleScreenshotCancel}
        onSave={handleScreenshotSave}
        screenshotDataUrl={screenshotDataUrl}
        isForcedScreenshot={isForcedScreenshot}
      />

      <ComponentAnnotationModal
        isOpen={showComponentModal}
        onClose={() => {
          setShowComponentModal(false);
          setSelectedComponent(null);
          setUIState(RecorderUIState.RECORDING);
        }}
        onSave={handleComponentSave}
        componentPreviewUrl={componentPreviewUrl}
      />

      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        bottom={0}
        pointerEvents="none"
        zIndex={1000}
        data-preview-window
      >
        {isReplaying && (
          <>
            <Box
              position="absolute"
              top={0}
              left={0}
              right={0}
              bottom={0}
              bg="rgba(0,0,150,0.05)"
              // More saturation using filter
              backdropFilter="saturate(1.2)"
              // pointerEvents="all"
              zIndex={1}
            />
            <Box
              position="absolute"
              top={2}
              right={2}
              bg="rgba(0, 0, 0, 0.2)"
              backdropFilter="blur(5px)"
              border="1px solid rgba(255, 255, 255, 0.1)"
              borderRadius="full"
              px={3}
              py={1}
              display="flex"
              alignItems="center"
              gap={2}
              zIndex={1}
            >
              <Spinner size="xs" color="blue.400" />
              <Text color="white" fontSize="sm" fontWeight="medium">
                Replaying
              </Text>
            </Box>
          </>
        )}

        <AnimatePresence>
          {clickAnimations.map((animation) => (
            <motion.div
              key={animation.id}
              initial={{ opacity: 1, scale: 1 }}
              animate={{ opacity: 0, scale: 1.2 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              style={{
                position: "absolute",
                top: animation.rect.top,
                left: animation.rect.left,
                width: animation.rect.width,
                height: animation.rect.height,
                border: "2px solid rgba(244, 67, 54, 0.8)",
                borderRadius: "4px",
                backgroundColor: "rgba(244, 67, 54, 0.1)",
                pointerEvents: "none",
                zIndex: 1000,
                animation: "pulseClick 1s ease-out",
              }}
            />
          ))}
        </AnimatePresence>

        <Box
          position="absolute"
          bottom="20px"
          left="50%"
          transform="translateX(-50%)"
          display="flex"
          flexDirection="column"
          alignItems="center"
          gap="10px"
          pointerEvents="none"
          width="auto"
          minWidth="280px"
          textAlign="center"
        >
          {activeRecording &&
            !isRecording &&
            activeRecording.events &&
            activeRecording.events.length > 0 && <Transcript />}

          {(uiState === RecorderUIState.REPLAYING || isReplaying) && (
            <>
              <motion.div
                layout
                initial={false}
                transition={{
                  type: "spring",
                  stiffness: 500,
                  damping: 35,
                  duration: 0.3,
                }}
                style={{
                  background: "rgba(20, 20, 20, 0.4)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "9999px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  padding: "8px",
                  pointerEvents: "auto",
                  width: "300px",
                  margin: "0 auto",
                }}
              >
                <Box
                  position="relative"
                  w="100%"
                  h="3px"
                  bg="rgba(255, 255, 255, 0.2)"
                  borderRadius="full"
                  overflow="hidden"
                >
                  <Box
                    h="100%"
                    w={`${replayProgress}%`}
                    bg="blue.500"
                    transition="width 0.3s ease"
                  />
                  {activeRecording?.consoleLogs.map((log, index) => (
                    <ConsoleLogMarker key={index} type={log.level} />
                  ))}
                </Box>
              </motion.div>
              <motion.div
                layout
                initial={false}
                transition={{
                  type: "spring",
                  stiffness: 500,
                  damping: 35,
                  duration: 0.3,
                }}
                style={{
                  background: "rgba(20, 20, 20, 0.4)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "9999px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  padding: "8px",
                  pointerEvents: "auto",
                  display: "inline-flex",
                  justifyContent: "center",
                  margin: "0 auto",
                }}
              >
                <Button
                  size="sm"
                  colorScheme="blue"
                  variant="ghost"
                  onClick={toggleReplay}
                  leftIcon={
                    <Box w="8px" h="8px" borderRadius="full" bg="blue.500" />
                  }
                  borderRadius="full"
                >
                  Stop
                </Button>
              </motion.div>
            </>
          )}

          {task.taskState === TaskState.IDLE &&
            uiState !== RecorderUIState.REPLAYING &&
            !isReplaying && (
              <motion.div
                layout
                initial={false}
                transition={{
                  type: "spring",
                  stiffness: 500,
                  damping: 35,
                  duration: 0.3,
                }}
                style={{
                  background: "rgba(20, 20, 20, 0.4)",
                  backdropFilter: "blur(10px)",
                  borderRadius: "9999px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  padding: "8px",
                  pointerEvents: "auto",
                  display: "inline-flex",
                  justifyContent: "center",
                  margin: "0 auto",
                  zIndex: 1002,
                }}
              >
                {renderControlPill()}
              </motion.div>
            )}
        </Box>

        <style jsx global>{`
          @keyframes pulseClick {
            0% {
              box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.4);
            }
            70% {
              box-shadow: 0 0 0 10px rgba(244, 67, 54, 0);
            }
            100% {
              box-shadow: 0 0 0 0 rgba(244, 67, 54, 0);
            }
          }
          @keyframes pulse {
            0% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
            100% {
              opacity: 1;
            }
          }
        `}</style>
      </Box>
    </>
  );
}
