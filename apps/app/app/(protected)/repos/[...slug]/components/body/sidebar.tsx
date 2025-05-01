import { closeTask } from "@/app/utils/functions/task";
import { useTaskStore } from "@/app/utils/stores/task";
import {
  Box,
  Flex,
  IconButton,
  Image,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import RepoSettingsButtonAndModal from "@components/repo-settings/button";
import { useSocket } from "@utils/socket";
import { useWebviewStore } from "@utils/stores/website-preview";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FaBrain } from "react-icons/fa";
import { GoSidebarCollapse, GoSidebarExpand } from "react-icons/go";
import { IoMdArrowRoundBack } from "react-icons/io";
import { MdChat } from "react-icons/md";

import { TaskState } from "@/app/types/task";
import PullRequestModal from "../headers/pull-request/modal";
import ChatWindow from "./chat/chat-window";
import WorkspaceWindow from "./workspace/workspace-window";

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);

interface SidebarLayoutProps {
  sidebarExpanded: boolean;
  setSidebarExpanded: (expanded: boolean) => void;
  isDragging: boolean;
}

const SidebarLayout = ({
  sidebarExpanded,
  setSidebarExpanded,
  isDragging,
}: SidebarLayoutProps) => {
  const [size, setSize] = useState("100vw");
  const { task, updateUIState } = useTaskStore();
  const { previewWidth, setWebviewSettings } = useWebviewStore();

  const router = useRouter();
  const { emit } = useSocket();

  useEffect(() => {
    setSize(`calc(${100 - previewWidth}% + 60px)`);
  }, [previewWidth, sidebarExpanded]);

  useEffect(() => {
    if (sidebarExpanded) {
      if (previewWidth > 70) {
        setWebviewSettings({
          previewWidth: 70,
        });
      }
    } else {
      setWebviewSettings({
        previewWidth: 100,
      });
    }
  }, [sidebarExpanded, previewWidth]);

  useEffect(() => {
    if (!task.uiState.activeTab) {
      updateUIState({ activeTab: "chat" });
    }
  }, []);

  const toggleSidebar = () => {
    const newExpandedState = !task.uiState.sidebarExpanded;
    setSidebarExpanded(newExpandedState);
  };

  const closePullRequestModal = () => {
    updateUIState({ gitPanelActive: false });
  };

  const onExitButtonClick = async () => {
    router.push("/home");
    emit("soft_close_task", {
      task_id: task.taskId,
    });
    await closeTask();
  };

  return (
    <MotionFlex
      h="100%"
      position="absolute"
      left="0"
      top="0"
      animate={{
        width: size,
      }}
      transition={{ duration: isDragging ? 0 : 0.2, ease: "easeOut" }}
      minW="60px"
    >
      {/* Sidebar Navigation Column */}
      <MotionFlex
        flexDirection="column"
        h="100%"
        w="60px"
        minW="60px"
        bgGradient="linear(to-b, rgba(0,30,50,0.5) 0%, rgba(0,0,0,0.3) 20%, rgba(0,0,0,0.3) 90%, rgba(0,30,50,0.5) 100%)"
        borderRight="1px solid"
        borderColor="rgba(255,255,255,0.1)"
      >
        {/* Top Navigation */}
        <VStack spacing={4} p={3} align="center" mb={4}>
          <Tooltip label="Back to Home" placement="right">
            <IconButton
              aria-label="Back"
              icon={<IoMdArrowRoundBack />}
              variant="ghost"
              colorScheme="red"
              size="sm"
              onClick={onExitButtonClick}
            />
          </Tooltip>
          {/* <Tooltip label="Save Changes" placement="right">
            <IconButton
              aria-label="Save"
              icon={<FaSave />}
              variant="ghost"
              colorScheme="blue"
              size="sm"
              onClick={() => updateUIState({ gitPanelActive: true })}
              isDisabled={!task.fileSystem.hasChanges}
            />
          </Tooltip> */}
          <Tooltip label="Settings" placement="right">
            <RepoSettingsButtonAndModal />
          </Tooltip>
          <PullRequestModal
            isOpen={task.uiState.gitPanelActive || false}
            onClose={closePullRequestModal}
          />
        </VStack>

        {/* Tab Navigation */}
        <VStack
          spacing={2}
          align="center"
          mt={4}
          borderTop="1px solid"
          borderBottom="1px solid"
          borderColor="rgba(255,255,255,0.05)"
          py={6}
        >
          {task.taskState > TaskState.RECORDING_SENT && (
            <Tooltip label="Chat" placement="right">
              <Flex
                as="button"
                py={2}
                borderRadius="md"
                align="center"
                justify="center"
                onClick={() =>
                  updateUIState({ activeTab: "chat", unreadMessages: false })
                }
                bg={
                  task.uiState.activeTab === "chat" ? "blue.900" : "transparent"
                }
                color={
                  task.uiState.activeTab === "chat" ? "blue.400" : "gray.400"
                }
                _hover={{
                  bg:
                    task.uiState.activeTab === "chat"
                      ? "blue.900"
                      : "whiteAlpha.100",
                }}
                transition="all 0.2s"
                w="40px"
                h="40px"
                position="relative"
              >
                <MdChat size="20px" />
                {task.uiState.unreadMessages && (
                  <Box
                    position="absolute"
                    top="1"
                    right="1"
                    bg="rgba(255,50,50,0.5)"
                    borderRadius="full"
                    minW="8px"
                    h="8px"
                    p="0"
                  />
                )}
              </Flex>
            </Tooltip>
          )}
          {task.taskState > TaskState.RECORDING_SENT && (
            <Tooltip label="Workspace" placement="right">
              <Flex
                as="button"
                py={2}
                borderRadius="md"
                align="center"
                justify="center"
                onClick={() => updateUIState({ activeTab: "workspace" })}
                bg={
                  task.uiState.activeTab === "workspace"
                    ? "blue.900"
                    : "transparent"
                }
                color={
                  task.uiState.activeTab === "workspace"
                    ? "blue.400"
                    : "gray.400"
                }
                _hover={{
                  bg:
                    task.uiState.activeTab === "workspace"
                      ? "blue.900"
                      : "whiteAlpha.100",
                }}
                transition="all 0.2s"
                w="40px"
                h="40px"
              >
                <FaBrain size="20px" />
              </Flex>
            </Tooltip>
          )}
        </VStack>

        {/* Bottom Area with Logo and Toggle */}
        <VStack
          mt="auto"
          p={3}
          borderTop="1px solid"
          borderColor="gray.700"
          spacing={8}
          align="center"
        >
          <Image
            src="/logos/no-bg/speck-logo-256.webp"
            alt="Speck Logo"
            w="20px"
            h="20px"
          />
          <IconButton
            aria-label={sidebarExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
            icon={
              sidebarExpanded ? (
                <GoSidebarExpand size={20} />
              ) : (
                <GoSidebarCollapse size={20} />
              )
            }
            onClick={toggleSidebar}
            variant="outline"
            size="sm"
            isDisabled={task.taskState === TaskState.IDLE}
          />
        </VStack>
      </MotionFlex>

      {/* Content Area */}
      <MotionBox
        h="100%"
        // bg="radial-gradient(circle at bottom, rgba(0,75,255,0.07) 0%, rgba(0,0,0,0.0) 80%)"
        animate={{
          width: sidebarExpanded ? "100%" : "0px",
        }}
        transition={{ duration: isDragging ? 0 : 0.2 }}
        overflow="hidden"
        position="relative"
        style={{ originX: 0 }}
      >
        {task.uiState.activeTab === "chat" && (
          <Box h="100%" w="100%">
            <ChatWindow />
          </Box>
        )}
        {task.uiState.activeTab === "workspace" && (
          <Box w="full" h="full">
            <WorkspaceWindow />
          </Box>
        )}
      </MotionBox>
    </MotionFlex>
  );
};

export default SidebarLayout;
