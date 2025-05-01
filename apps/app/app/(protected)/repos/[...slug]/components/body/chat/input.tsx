import { TaskState } from "@/app/types/task";
import {
  Avatar,
  Box,
  HStack,
  IconButton,
  Text,
  Textarea,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { AnimatePresence } from "@components/animated";
import { RadialIconButton } from "@components/radial-button";
import { ChatMessageRole } from "@ctypes/chat-message";
import { useSocket } from "@utils/socket";
import { motion } from "framer-motion";
import React, { useEffect, useState } from "react";

import { useTaskStore } from "@/app/utils/stores/task";
import { AttachmentIcon } from "@chakra-ui/icons";
import { Recording, toSnakeCase } from "@ctypes/recording";
import { FaArrowUp } from "react-icons/fa6";
import { BeatLoader } from "react-spinners";
import { AttachmentsBox } from "./attachments";

interface ChatInputProps {
  messageSentSignal: number;
}
export default function ChatInput({ messageSentSignal }: ChatInputProps) {
  const { task, updateTask, addNewMessage } = useTaskStore();
  const [inputText, setInputText] = useState("");
  const { emit } = useSocket();
  const [attachmentsOpen, setAttachmentsOpen] = useState(false);
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [cancellingTask, setCancellingTask] = useState(false);

  const canContinue = () => {
    if (task.taskState === TaskState.IDLE && inputText.length > 0) {
      return true;
    }
    return false;
  };

  const handleSendMessage = async () => {
    if (task.taskState !== TaskState.IDLE) {
      console.warn("task is not idle");
      return;
    }

    try {
      const textarea = document.querySelector(
        'textarea[placeholder="Type your message..."]',
      );
      if (textarea instanceof HTMLTextAreaElement) {
        textarea.style.height = "inherit";
      }
    } catch (error) {
      console.warn("Failed to reset textarea height:", error);
    }

    // updateTask({
    //   taskState: TaskState.CHAT_SENT,
    // });

    // TODO: FIX THIS

    addNewMessage({
      role: ChatMessageRole.USER,
      messageData: {
        mainMessage: {
          message: inputText,
        },
        attachments: {
          recordings: recordings,
        },
      },
    });

    emit("user_message", {
      task_id: task.taskId,
      git_repo_id: task.currentWorkspace?.gitRepoId,
      workspace_name: task.currentWorkspace?.workspaceName,
      message: inputText,
      recordings: recordings.map((recording) => toSnakeCase(recording)),
    });

    setRecordings([]);
    setInputText("");
    setAttachmentsOpen(false);
  };

  useEffect(() => {
    setRecordings([]);
    setInputText("");
    setAttachmentsOpen(false);
  }, [messageSentSignal]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    e.target.style.height = "inherit";
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const cancelTask = () => {
    setCancellingTask(true);
    emit("stop_task", {
      task_id: task.taskId,
    });
  };

  useEffect(() => {
    if (
      task.taskState === TaskState.IDLE ||
      task.taskState === TaskState.DONE
    ) {
      setCancellingTask(false);
    }
  }, [task.taskState]);

  return (
    <VStack
      bottom={0}
      right={0}
      w="full"
      spacing={2}
      justifyContent="center"
      alignItems="flex-end"
      px={2}
      zIndex={10}
    >
      {(recordings?.length ?? 0) > 0 && (
        <AttachmentsBox
          isOpen={attachmentsOpen}
          recordings={recordings}
          setRecordings={setRecordings}
        />
      )}
      <HStack
        w="full"
        minH="32px"
        justifyContent="space-between"
        borderTopRadius="xl"
        borderBottomRadius="none"
        bg="rgba(32,35,40,0.9)"
        backdropFilter="blur(10px)"
        borderTopWidth={1}
        borderLeftWidth={1}
        borderRightWidth={1}
        borderBottomWidth={0}
        borderColor="rgba(255,255,255,0.05)"
        p={0.5}
        px={1}
        zIndex={10}
        alignItems="flex-start"
      >
        <AnimatePresence>
          {1 > 2 && ( // TODO: Actually check this
            <motion.div
              initial={{ opacity: 0, y: 0 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                width: "calc(100% - 60px)",
                position: "absolute",
                top: "-30px",
                left: "30px",
              }}
            >
              <HStack
                w="full"
                justifyContent="space-between"
                borderWidth={1}
                borderColor="rgba(255,255,255,0.1)"
                borderTopRadius="lg"
                borderBottom={0}
                p={1}
                px={4}
                bg="rgba(0,10,25,1)"
                zIndex={10}
                alignItems="center"
              >
                <HStack h="full">
                  <Avatar
                    height="20px"
                    width="20px"
                    src="/logos/no-bg/speck-logo-512.webp"
                  />
                  <Text fontSize="xs" color="gray.400">
                    Speck is working...
                  </Text>
                </HStack>
                <BeatLoader size={5} color="white" />
              </HStack>
            </motion.div>
          )}
        </AnimatePresence>
        {task.taskState !== TaskState.IDLE && (
          <Box position="relative">
            <Tooltip label={"Attach context"} placement="top" fontSize="2xs">
              <IconButton
                icon={<AttachmentIcon />}
                borderRadius="xl"
                aria-label="Attach file"
                onClick={() => setAttachmentsOpen(!attachmentsOpen)}
                h="35px"
                w="35px"
                mt={0.5}
              />
            </Tooltip>
          </Box>
        )}
        {/* {task.taskState !== TaskState.IDLE && (
          <IconButton
            icon={
              <motion.div
                animate={{
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                }}
              >
                <BsStopCircle />
              </motion.div>
            }
            isLoading={cancellingTask}
            onClick={cancelTask}
            aria-label="Cancel task"
            borderRadius="xl"
            as={motion.button}
            animate={{
              height: ["35px", "40px", "35px"],
              width: ["35px", "40px", "35px"],
            }}
            transition={{
              duration: "2s",
              repeat: "infinite",
              ease: "circOut",
            }}
            mt={0.5}
          />
        )} */}

        <Textarea
          value={inputText}
          onChange={handleTextareaChange}
          onKeyDown={handleKeyPress}
          placeholder="Type your message..."
          w="95%"
          minH="32px"
          maxH="150px"
          size="sm"
          variant="unstyled"
          ml={2}
          disabled={task.taskState !== TaskState.IDLE}
          resize="none"
          rows={1}
          my={1}
          pt={2}
          sx={{
            lineHeight: "normal",
          }}
        />
        <RadialIconButton
          icon={FaArrowUp}
          onClick={handleSendMessage}
          isDisabled={!canContinue()}
          bg={["rgba(60,153,255,1)", "rgba(10,123,250,0.7)"]}
          border="none"
          boxShadow="none"
          borderRadius="xl"
          h="35px"
          w="35px"
          mt={0.5}
          aria-label="Send message"
        />
      </HStack>
    </VStack>
  );
}
