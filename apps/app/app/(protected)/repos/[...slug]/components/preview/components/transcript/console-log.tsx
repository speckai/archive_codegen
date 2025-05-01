import { ConsoleLog } from "@/app/types/recording";
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Text,
} from "@chakra-ui/react";
import { BiSolidError } from "react-icons/bi";
import { BsTerminal } from "react-icons/bs";
import { IoWarning } from "react-icons/io5";

interface ConsoleLogEntryProps {
  log: ConsoleLog;
}

export default function ConsoleLogEntry({ log }: ConsoleLogEntryProps) {
  const minutes = Math.floor(log.timestamp / 60000);
  const seconds = Math.floor((log.timestamp % 60000) / 1000);
  const timestamp = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  return (
    <Accordion allowToggle>
      <AccordionItem border="none">
        <Box
          as={log.traceback ? AccordionButton : "div"}
          p={2}
          borderBottom="1px solid rgba(255, 255, 255, 0.1)"
          bg={
            log.level === "error"
              ? "rgba(244, 67, 54, 0.1)"
              : log.level === "warn"
                ? "rgba(255, 152, 0, 0.1)"
                : "transparent"
          }
          display="flex"
          alignItems="center"
          gap={2}
          cursor={log.traceback ? "pointer" : "default"}
          _hover={
            log.traceback
              ? {
                  bg:
                    log.level === "error"
                      ? "rgba(244, 67, 54, 0.15)"
                      : log.level === "warn"
                        ? "rgba(255, 152, 0, 0.15)"
                        : "rgba(255, 255, 255, 0.05)",
                }
              : undefined
          }
          w="100%"
        >
          <Box
            color={
              log.level === "error"
                ? "red.400"
                : log.level === "warn"
                  ? "orange.400"
                  : "blue.400"
            }
            fontSize="14px"
            display="flex"
            alignItems="center"
          >
            {log.level === "error" ? (
              <BiSolidError />
            ) : log.level === "warn" ? (
              <IoWarning />
            ) : (
              <BsTerminal />
            )}
          </Box>
          <Box
            flex="1"
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            gap={4}
          >
            <Text
              fontSize="xs"
              color={
                log.level === "error"
                  ? "red.400"
                  : log.level === "warn"
                    ? "orange.400"
                    : "gray.300"
              }
              fontFamily="monospace"
              whiteSpace="pre-wrap"
              wordBreak="break-word"
              lineHeight="1.4"
              textAlign="left"
            >
              {log.output}
            </Text>
            <Text
              fontSize="xs"
              color="gray.500"
              fontFamily="monospace"
              lineHeight="1"
            >
              {timestamp}
            </Text>
          </Box>
          {log.traceback && <AccordionIcon color="gray.500" ml={2} />}
        </Box>
        {log.traceback && (
          <AccordionPanel p={0}>
            <Box
              bg="rgba(0, 0, 0, 0.2)"
              pl={3}
              pr={2}
              py={2}
              borderBottom="1px solid rgba(255, 255, 255, 0.1)"
              borderLeft="3px solid rgba(244, 67, 54, 0.15)"
            >
              {log.traceback.map((trace, traceIndex) => (
                <Text
                  key={traceIndex}
                  fontSize="2xs"
                  color="gray.400"
                  fontFamily="monospace"
                  whiteSpace="pre-wrap"
                  wordBreak="break-word"
                  textAlign="left"
                >
                  {trace}
                </Text>
              ))}
            </Box>
          </AccordionPanel>
        )}
      </AccordionItem>
    </Accordion>
  );
}
