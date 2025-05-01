import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
  Code,
  HStack,
  Icon,
  Text,
  VStack,
} from "@chakra-ui/react";
import "@mdxeditor/editor/style.css";
import { FiInfo } from "react-icons/fi";
import { IoWarningOutline } from "react-icons/io5";
import { MdErrorOutline } from "react-icons/md";
import { SlMagnifier } from "react-icons/sl";
import ReactMarkdown from "react-markdown";

interface ConsoleLogViewerProps {
  logData: any;
}

export default function ConsoleLogViewer({ logData }: ConsoleLogViewerProps) {
  const getLogIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case "error":
        return { icon: MdErrorOutline, color: "red.300" };
      case "warn":
        return { icon: IoWarningOutline, color: "orange.400" };
      default:
        return { icon: FiInfo, color: "blue.300" };
    }
  };

  if (!logData) return <Text color="white">Log data not found</Text>;

  const { icon: LogIcon, color: logColor } = getLogIcon(logData.data.log.level);

  return (
    <Accordion allowToggle width="100%" my={4}>
      <AccordionItem
        border="1px"
        borderColor={"rgba(255,255,255,0.1)"}
        borderRadius="md"
      >
        <AccordionButton
          bg="rgba(0,0,0,0.3)"
          _hover={{ bg: "rgba(0, 0, 0, 0.4)" }}
        >
          <Box flex="1" textAlign="left" fontWeight="medium">
            <HStack spacing={2}>
              <Icon as={LogIcon} color={logColor} boxSize={4} />
              <Text
                color={
                  logData.data.log.level === "error"
                    ? "red.300"
                    : logData.data.log.level === "warn"
                      ? "orange.400"
                      : "gray.300"
                }
                fontSize="sm"
              >
                {logData.data.title}
              </Text>
            </HStack>
          </Box>
          <AccordionIcon color="white" />
        </AccordionButton>
        <AccordionPanel pb={4} bg="rgba(0, 0, 0, 0.2)">
          <VStack align="start" spacing={4} width="100%">
            <Text fontWeight="bold" color="white">
              Description:
            </Text>
            {logData.data.description && (
              <Box className="description-markdown" px={4}>
                <ReactMarkdown>{logData.data.description}</ReactMarkdown>
              </Box>
            )}

            <Box width="100%" fontFamily="mono">
              <HStack
                spacing={2}
                p={2}
                borderBottom="1px"
                borderColor="whiteAlpha.200"
              >
                <Icon as={LogIcon} color={logColor} />
                <Text fontWeight="bold" color="white">
                  Console
                </Text>
              </HStack>
              <VStack spacing={0} align="stretch">
                <Box p={4} borderRadius="md" fontSize="sm">
                  <Code
                    display="block"
                    whiteSpace="pre-wrap"
                    wordBreak="break-word"
                    bg="transparent"
                    color="white"
                    children={logData.data.log.output}
                  />
                </Box>

                {logData.data.log.traceback &&
                  logData.data.log.traceback.length > 0 && (
                    <VStack pl={4} spacing={0}>
                      <HStack w="full">
                        <Icon
                          as={SlMagnifier}
                          color="gray.400"
                          boxSize={3}
                          mb={1}
                        />
                        <Text
                          fontSize="2xs"
                          color="gray.400"
                          mb={1}
                          textAlign="left"
                          w="full"
                        >
                          Trace:
                        </Text>
                      </HStack>
                      <VStack fontSize="sm" spacing={2} w="full">
                        {logData.data.log.traceback.map(
                          (line: string, i: number) => (
                            <Code
                              key={i}
                              display="block"
                              whiteSpace="pre-wrap"
                              wordBreak="break-word"
                              bg="transparent"
                              color={
                                line.trim().startsWith("File")
                                  ? "blue.300"
                                  : line.includes("Error:")
                                    ? "red.300"
                                    : "white"
                              }
                              pl={line.trim().startsWith("File") ? 0 : 4}
                              children={line}
                              textAlign="left"
                              w="full"
                              fontSize="xs"
                            />
                          ),
                        )}
                      </VStack>
                    </VStack>
                  )}
              </VStack>
            </Box>

            <Text fontWeight="bold" mt={2} color="white">
              Context:
            </Text>
            <Text color="white">{logData.data.context}</Text>
          </VStack>
        </AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
}
