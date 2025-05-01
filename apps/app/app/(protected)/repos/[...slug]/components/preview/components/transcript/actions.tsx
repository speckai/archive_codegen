import { RecordingEvent } from "@/app/types/recording";
import { Box, HStack, Text, VStack } from "@chakra-ui/react";
import { BsArrowsMove, BsCamera } from "react-icons/bs";
import { FaKeyboard, FaMousePointer, FaReact } from "react-icons/fa";

interface ActionsProps {
  events: RecordingEvent[];
  currentActionIndex: number;
}

export default function Actions({ events, currentActionIndex }: ActionsProps) {
  return (
    <VStack
      spacing={1}
      align="stretch"
      maxH="200px"
      minW="300px"
      overflowY="auto"
      overflowX="hidden"
    >
      {events
        .filter((event) => event.type !== "terminate")
        .map((event, index) => {
          let totalDelay = 0;
          for (let i = 0; i <= index; i++) {
            totalDelay += events[i].delay || 0;
          }
          const timeFromStart = event.timestamp || totalDelay;
          const minutes = Math.floor(timeFromStart / 60000);
          const seconds = Math.floor((timeFromStart % 60000) / 1000);
          const timestamp = `${minutes}:${seconds.toString().padStart(2, "0")}`;

          return (
            <Box
              key={index}
              p={2}
              borderRadius="md"
              bg={
                currentActionIndex === index
                  ? "rgba(33, 150, 243, 0.4)"
                  : "transparent"
              }
              transition="transform 0.2s ease"
              transform={
                currentActionIndex === index
                  ? "translateX(3px)"
                  : "translateX(0)"
              }
              data-action-index={index}
            >
              <HStack justify="space-between">
                <HStack spacing={2} align="center">
                  <Box
                    color={currentActionIndex === index ? "white" : "gray.400"}
                  >
                    {event.type === "click" ? (
                      <FaMousePointer size="12px" />
                    ) : event.type === "scroll" ? (
                      <BsArrowsMove size="12px" />
                    ) : event.type === "input" || event.type === "change" ? (
                      <FaKeyboard size="12px" />
                    ) : event.type === "component_selection" ? (
                      <FaReact size="12px" />
                    ) : event.type === "screenshot" ? (
                      <BsCamera size="12px" />
                    ) : null}
                  </Box>
                  <Text fontSize="xs" color="white">
                    {timestamp}
                  </Text>
                </HStack>
                <Text fontSize="xs" color="white">
                  {event.type === "click"
                    ? "Click"
                    : event.type === "scroll"
                      ? "Scroll"
                      : event.type === "input" || event.type === "change"
                        ? "Input"
                        : event.type === "component_selection"
                          ? "Selected Component"
                          : event.type === "screenshot"
                            ? "Screenshot"
                            : event.type}
                  {event.target?.innerText
                    ? ` "${event.target.innerText.substring(0, 20)}${
                        event.target.innerText.length > 20 ? "..." : ""
                      }"`
                    : ""}
                </Text>
              </HStack>
            </Box>
          );
        })}
    </VStack>
  );
}
