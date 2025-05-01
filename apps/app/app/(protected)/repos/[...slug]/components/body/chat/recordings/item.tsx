import { Recording } from "@/app/types/recording";
import { RecorderUIState, useRecorderStore } from "@/app/utils/stores/recorder";
import {
  Box,
  HStack,
  IconButton,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import React from "react";
import { FaPlay, FaTimes } from "react-icons/fa";
import { RiRecordCircleFill } from "react-icons/ri";

interface RecordingItemProps {
  recording: Recording;
  recordings: Recording[];
  setRecordings: React.Dispatch<React.SetStateAction<Recording[]>>;
}

export default function RecordingItem({
  recording,
  recordings,
  setRecordings,
}: RecordingItemProps) {
  const { setActiveRecording, setUIState, setShowInfoPanel } =
    useRecorderStore();

  const handleRemove = () => {
    setRecordings(recordings.filter((r) => r.id !== recording.id));
  };

  const loadRecording = (recording: Recording) => {
    const iframe = document.getElementById(
      "speck-preview-iframe",
    ) as HTMLIFrameElement;
    if (iframe?.contentWindow) {
      setActiveRecording(recording);
      setUIState(RecorderUIState.LOADED_RECORDING);
      setShowInfoPanel(true);

      iframe.contentWindow.postMessage(
        {
          type: "set_recording_data",
          data: {
            events: recording.events,
            consoleLogs: recording.consoleLogs,
            initialUrl: recording.initialUrl,
            duration: recording.duration,
          },
        },
        "*",
      );
    }
  };

  return (
    <Box
      borderWidth={1}
      borderColor="rgba(255, 255, 255, 0.1)"
      borderRadius="md"
      p={2}
      bg="rgba(20, 20, 30, 0.7)"
      backdropFilter="blur(5px)"
      minW="180px"
      maxW="250px"
      position="relative"
    >
      <IconButton
        icon={<FaTimes />}
        aria-label="Remove recording"
        size="xs"
        position="absolute"
        top={1}
        right={1}
        borderRadius="full"
        variant="ghost"
        onClick={handleRemove}
      />
      <VStack spacing={1} align="start">
        <HStack>
          <RiRecordCircleFill color="red" />
          <Text fontSize="xs" fontWeight="bold" noOfLines={1}>
            {recording.name}
          </Text>
        </HStack>
        <HStack
          spacing={3}
          fontSize="2xs"
          color="gray.300"
          w="full"
          justify="space-between"
        >
          <HStack spacing={1}>
            <Text>Events:</Text>
            <Text fontWeight="bold">{recording.events.length}</Text>
          </HStack>
          <HStack spacing={1}>
            <Text>Duration:</Text>
            <Text fontWeight="bold">
              {(recording.duration / 1000).toFixed(1)}s
            </Text>
          </HStack>
        </HStack>
        {recording.annotation && (
          <Text fontSize="2xs" color="gray.300" noOfLines={2} w="full">
            {recording.annotation}
          </Text>
        )}
        <Tooltip label="Load recording in preview">
          <IconButton
            size="xs"
            icon={<FaPlay />}
            aria-label="Load recording"
            borderRadius="full"
            mt={1}
            onClick={() => loadRecording(recording)}
          />
        </Tooltip>
      </VStack>
    </Box>
  );
}
