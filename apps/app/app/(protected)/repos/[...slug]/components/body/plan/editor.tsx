import { RadialButton } from "@/app/components/radial-button";
import { useTaskStore } from "@/app/utils/stores/task";
import {
  Box,
  Button,
  Center,
  Flex,
  HStack,
  Icon,
  IconButton,
  Image,
  Modal,
  Spinner,
  Text,
  Tooltip,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import { keyframes } from "@chakra-ui/system";
import {
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { BugReport, convertToSnakeCase } from "@ctypes/bug-report";
import { TaskState } from "@ctypes/task";
import {
  codeBlockPlugin,
  headingsPlugin,
  imagePlugin,
  linkDialogPlugin,
  linkPlugin,
  listsPlugin,
  markdownShortcutPlugin,
  MDXEditor,
  quotePlugin,
  tablePlugin,
  thematicBreakPlugin,
} from "@mdxeditor/editor";
import "@mdxeditor/editor/style.css";
import { useSocket } from "@utils/socket";
import { useEffect, useState } from "react";
import { BsFillCursorFill } from "react-icons/bs";
import { FaPen } from "react-icons/fa";
import { FiRotateCcw } from "react-icons/fi";
import { MdBugReport } from "react-icons/md";

import { IoIosLaptop } from "react-icons/io";
import ConsoleLogViewer from "./console-log-viewer";
import { customStyles } from "./styles";
import SubmitConfirmation from "./submit-confirmation";

const splitByAssetsAndCodeBlocks = (markdown: string): string[] => {
  const assetRegex = /!\[.*?\]\(.*?\)|!\[.*?\]\((console_log_[a-z0-9]+)\)/g;
  const codeBlockRegex = /```(?:[a-zA-Z0-9]*\n)?([\s\S]*?)```/g;

  const combinedRegex = new RegExp(
    `${assetRegex.source}|${codeBlockRegex.source}`,
    "g",
  );

  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = combinedRegex.exec(markdown)) !== null) {
    if (match.index > lastIndex) {
      parts.push(markdown.substring(lastIndex, match.index));
    }

    parts.push(match[0]);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < markdown.length) {
    parts.push(markdown.substring(lastIndex));
  }

  return parts;
};

export const CodeBlockRenderer = ({
  code,
  language = "",
}: {
  code: string;
  language?: string;
}) => {
  return (
    <Box
      p={2}
      width="100%"
      borderRadius="md"
      bg="rgba(20, 40, 60, 0.4)"
      border="1px solid rgba(255, 255, 255, 0.1)"
      fontFamily="monospace"
      whiteSpace="pre-wrap"
      overflow="none"
      color="rgba(255, 255, 255, 0.8)"
      fontSize="sm"
    >
      {code}
    </Box>
  );
};

const cursorAnimation = keyframes`
  0% { transform: translate(30%, 15%) rotate(-15deg); }
  16.67% { transform: translate(40%, 40%) rotate(10deg); }
  33.33% { transform: translate(45%, 30%) rotate(-5deg); }
  50% { transform: translate(10%, 40%) rotate(15deg); }
  66.67% { transform: translate(45%, 30%) rotate(-10deg); }
  83.33% { transform: translate(35%, 40%) rotate(5deg); }
  100% { transform: translate(30%, 15%) rotate(-15deg); }
`;

const dotsAnimation = keyframes`
  0% { content: '.'; }
  33% { content: '..'; }
  66% { content: '...'; }
  100% { content: '.'; }
`;

const LoadingDots = () => (
  <Box
    as="span"
    sx={{
      "&::after": {
        content: "'.'",
        animation: `${dotsAnimation} 2s infinite steps(1)`,
      },
    }}
  />
);

const ReplayingAnimation = () => {
  const { task } = useTaskStore();

  return (
    <Center h="calc(100vh - 200px)" flexDirection="column" position="relative">
      <Box position="relative" w="75px" h="75px">
        <Box position="absolute" top="0" left="0" w="100%" h="100%">
          <IoIosLaptop size={75} color="rgba(255,255,255,0.7)" />
        </Box>
        <Box
          position="absolute"
          top="0"
          left="0"
          w="100%"
          h="100%"
          animation={`${cursorAnimation} 3s infinite ease-in-out`}
        >
          <BsFillCursorFill
            size={10}
            color="rgba(100,200,255,0.6)"
            style={{ zIndex: 1000 }}
          />
        </Box>
      </Box>
      <Text color="white" fontSize="lg" fontWeight="medium" mt={2}>
        Reproducing recording
        <LoadingDots />
      </Text>
      {task.recorderProgress && (
        <Text
          color="rgba(255,255,255,0.7)"
          fontSize="sm"
          fontWeight="light"
          mt={2}
        >
          {task.recorderProgress?.index} / {task.recorderProgress?.total} (
          {task.recorderProgress?.type})
        </Text>
      )}
    </Center>
  );
};

export const AssetRenderer = ({
  assetUrl,
  assetType,
  altText = "Bug report asset",
}: {
  assetUrl: string;
  assetType: "image" | "video";
  altText?: string;
}) => {
  if (assetType === "image") {
    return (
      <Image
        src={assetUrl}
        alt={altText}
        width="100%"
        height="auto"
        maxH="800px"
        objectFit="contain"
        loading="lazy"
        borderRadius="xl"
      />
    );
  } else if (assetType === "video") {
    return (
      <Box borderRadius="md" maxW="100%" boxShadow="md">
        <video controls width="100%">
          <source src={assetUrl} type="video/webm" />
          Your browser does not support the video tag.
        </video>
      </Box>
    );
  }

  return null;
};

export default function Editor() {
  const [bugReport, setBugReport] = useState<BugReport | null>(null);
  const [markdownParts, setMarkdownParts] = useState<string[]>([]);
  const [originalParts, setOriginalParts] = useState<string[]>([]);
  const [resetCounter, setResetCounter] = useState(0);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isResetOpen,
    onOpen: onResetOpen,
    onClose: onResetClose,
  } = useDisclosure();
  const { emit } = useSocket();
  const { task, updateTask } = useTaskStore();

  useEffect(() => {
    if (!task.bugReport) {
      return;
    }

    setBugReport(task.bugReport);

    if (task.bugReport?.report) {
      const parts = splitByAssetsAndCodeBlocks(task.bugReport.report);
      setMarkdownParts([...parts]);
      setOriginalParts(JSON.parse(JSON.stringify(parts)));
    }
  }, [task.bugReport]);

  const handleReset = () => {
    onResetOpen();
  };

  const confirmReset = () => {
    const resetParts = JSON.parse(JSON.stringify(originalParts));
    setMarkdownParts(resetParts);
    setResetCounter((prev) => prev + 1);
    onResetClose();
  };

  const handleSubmit = () => {
    onOpen();
  };

  const getFinalMarkdown = () => {
    return markdownParts.join("\n\n");
  };

  const onSubmit = () => {
    const finalReport = convertToSnakeCase({
      report: getFinalMarkdown(),
      asset_urls: bugReport?.assetUrls || {},
      text_models: bugReport?.textModels || {},
    });

    emit("submit_report", {
      task_id: task.taskId,
      git_repo_id: task.currentWorkspace?.gitRepoId,
      workspace_name: task.currentWorkspace?.workspaceName,
      report_data: finalReport,
    });
    updateTask({
      bugReport: {
        report: getFinalMarkdown(),
        assetUrls: bugReport?.assetUrls || {},
        textModels: bugReport?.textModels || {},
      },
      taskState: TaskState.BUG_REPORT_SUBMITTED,
    });
    onClose();
  };

  useEffect(() => {
    setResetCounter((prev) => prev + 1);
  }, [bugReport]);

  if (!bugReport) {
    if (task.taskState === TaskState.REPLAYING_RECORDING) {
      return <ReplayingAnimation />;
    }

    return (
      <Center h="calc(100vh - 200px)">
        <Flex direction="column" align="center" gap={4}>
          <Spinner
            emptyColor="rgba(255,255,255,0.05)"
            color="rgba(100,200,255,0.7)"
            size="lg"
          />
          <Text color="white" fontSize="lg" fontWeight="medium">
            Generating bug report
            <LoadingDots />
          </Text>
        </Flex>
      </Center>
    );
  }

  return (
    <Box width="100%" height="100%" display="flex" flexDirection="column">
      <style>{customStyles}</style>

      {/* Action Buttons */}
      {task.taskState < TaskState.BUG_REPORT_SUBMITTED && (
        <HStack
          px={4}
          pb={3}
          justify="space-between"
          borderBottom="1px solid rgba(255,255,255,0.1)"
        >
          <HStack spacing={3}>
            <MdBugReport size={18} />
            <Text fontSize="md" fontWeight="bold">
              Edit Report
            </Text>
          </HStack>
          <HStack spacing={2}>
            <Tooltip label="Reset Changes" placement="bottom">
              <IconButton
                aria-label="Reset changes"
                icon={<FiRotateCcw />}
                variant="outline"
                colorScheme="red"
                size="sm"
                borderRadius="lg"
                onClick={handleReset}
              />
            </Tooltip>
            <RadialButton
              colorScheme="blue"
              size="sm"
              onClick={handleSubmit}
              icon={<FaPen />}
              boxShadow="none"
              borderRadius="lg"
            >
              Submit
            </RadialButton>
          </HStack>
        </HStack>
      )}

      {/* Editor Content */}
      <VStack
        align="stretch"
        flex={1}
        overflow="auto"
        p={4}
        spacing={4}
        border={
          task.taskState === TaskState.BUG_REPORT_GENERATED
            ? "1px solid rgba(255,255,255,0.1)"
            : "none"
        }
        borderRadius="lg"
        mt={2}
        minH="400px"
        bg="rgba(255,255,255,0.03)"
      >
        {task.taskState === TaskState.BUG_REPORT_GENERATED && (
          <HStack mb={-8} w="full" justifyContent="center">
            <Icon as={FaPen} boxSize={3} />
            <Text fontSize="xs" fontStyle="italic">
              Editing
            </Text>
          </HStack>
        )}

        {markdownParts.map((part, index) => {
          if (part.startsWith("```")) {
            const matches = part.match(/```(?:([a-zA-Z0-9]*)\n)?([\s\S]*?)```/);
            if (matches) {
              const language = matches[1] || "";
              const code = matches[2] || "";
              return (
                <CodeBlockRenderer
                  key={`code-${index}`}
                  code={code}
                  language={language}
                />
              );
            }
          }

          if (
            part.startsWith("![") &&
            part.includes("](") &&
            (Object.keys(bugReport.textModels).length > 0 ||
              Object.keys(bugReport.assetUrls).length > 0)
          ) {
            const match = part.match(/!\[(.*?)\]\((.*?)\)/);
            if (match && match[2]) {
              const altText = match[1];
              const assetRef = match[2];

              if (assetRef.startsWith("console_log_")) {
                const logData = bugReport.textModels[assetRef];
                return <ConsoleLogViewer key={index} logData={logData} />;
              }

              const assetUrl = bugReport.assetUrls[assetRef];
              if (assetUrl) {
                const isVideo =
                  assetUrl.includes(".webm") || assetUrl.includes(".mp4");
                return (
                  <AssetRenderer
                    key={index}
                    assetUrl={assetUrl}
                    assetType={isVideo ? "video" : "image"}
                    altText={altText}
                  />
                );
              }

              if (assetRef.startsWith("http")) {
                const isVideo =
                  assetRef.includes(".webm") || assetRef.includes(".mp4");
                return (
                  <AssetRenderer
                    key={index}
                    assetUrl={assetRef}
                    assetType={isVideo ? "video" : "image"}
                    altText={altText}
                  />
                );
              }

              return (
                <Text key={index} color="white">
                  {part}
                </Text>
              );
            }

            return (
              <Text key={index} color="white">
                {part}
              </Text>
            );
          }

          return (
            <Box
              key={`editor-${index}-${resetCounter}`}
              width="100%"
              border="none"
              borderRadius="md"
            >
              <MDXEditor
                markdown={part}
                onChange={(markdown) => {
                  if (task.taskState !== TaskState.BUG_REPORT_GENERATED) {
                    return;
                  }
                  const newParts = [...markdownParts];
                  newParts[index] = markdown;
                  setMarkdownParts(newParts);
                }}
                readOnly={task.taskState !== TaskState.BUG_REPORT_GENERATED}
                contentEditableClassName="prose max-w-none"
                plugins={[
                  headingsPlugin(),
                  listsPlugin(),
                  quotePlugin(),
                  thematicBreakPlugin(),
                  markdownShortcutPlugin(),
                  codeBlockPlugin(),
                  linkPlugin(),
                  linkDialogPlugin(),
                  imagePlugin(),
                  tablePlugin(),
                ]}
                className="mdx-editor"
              />
            </Box>
          );
        })}
      </VStack>

      {/* Submit Confirmation Modal */}
      <SubmitConfirmation
        isOpen={isOpen}
        onClose={onClose}
        onSubmit={onSubmit}
        markdown={getFinalMarkdown()}
        bugReport={bugReport}
      />

      {/* Reset Confirmation Modal */}
      <Modal isOpen={isResetOpen} onClose={onResetClose} size="sm" isCentered>
        <ModalOverlay />
        <ModalContent bg="gray.900" color="white">
          <ModalHeader>Confirm Reset</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text>
              Are you sure you want to reset all changes? This action cannot be
              undone.
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onResetClose}>
              Cancel
            </Button>
            <Button colorScheme="red" onClick={confirmReset}>
              Reset
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
