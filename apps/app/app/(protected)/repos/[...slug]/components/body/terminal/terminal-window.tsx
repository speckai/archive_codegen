"use client";

import { useTaskStore } from "@/app/utils/stores/task";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import { Box, HStack, IconButton, Text, VStack } from "@chakra-ui/react";
import { LogType } from "@ctypes/terminal";
import { useConsoleStore } from "@utils/stores/console";
import { useEffect, useRef } from "react";

const Logs = () => {
  const { outputs } = useConsoleStore();
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView();
  }, [outputs]);

  return (
    <VStack
      px={4}
      fontFamily="monospace"
      fontSize="xs"
      color="white"
      align="start"
      spacing={0.5}
      h="full"
      w="full"
      overflowY="auto"
    >
      {outputs.map((log, index) => (
        <Text
          key={index}
          color={
            log.logType === LogType.ERROR
              ? "red.300"
              : log.logType === LogType.USER
                ? "blue.300"
                : "white"
          }
          whiteSpace="pre-wrap"
          fontWeight={log.logType === LogType.USER ? "bold" : "normal"}
          // If the last line then add spacing
          {...(index === outputs.length - 1 && { pb: 8 })}
        >
          {log.logType === LogType.USER ? "$ " : ""}
          {log.line.trim()}
        </Text>
      ))}
      <div ref={logsEndRef} />
    </VStack>
  );
};

const Header = () => {
  const { updateUIState } = useTaskStore();

  return (
    <HStack justify="space-between" w="full" px={2} mt={2}>
      <Box flex={1} />
      <Box flex={1} textAlign="center">
        <Text fontSize="xs">Terminal</Text>
      </Box>
      <HStack flex={1} justify="flex-end">
        <IconButton
          icon={<ChevronUpIcon />}
          aria-label="Maximize"
          rounded="full"
          size="xs"
          onClick={() => updateUIState({ terminalShown: true })}
        />
        <IconButton
          icon={<ChevronDownIcon />}
          aria-label="Minimize"
          rounded="full"
          size="xs"
          onClick={() => updateUIState({ terminalShown: false })}
        />
      </HStack>
    </HStack>
  );
};

export default function TerminalWindow() {
  return (
    <VStack
      h="full"
      w="full"
      bg="rgba(0,0,0,1)"
      borderTop="1px solid rgba(255,255,255,0.25)"
      zIndex={1000}
    >
      <Header />
      <Logs />
    </VStack>
  );
}
