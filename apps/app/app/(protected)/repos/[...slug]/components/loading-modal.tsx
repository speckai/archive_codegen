"use client";

import { LoadingTaskState } from "@/app/types/task";
import { closeTask } from "@/app/utils/functions/task";
import { useTaskStore } from "@/app/utils/stores/task";
import { ArrowBackIcon, ChevronLeftIcon, SettingsIcon } from "@chakra-ui/icons";
import {
  Box,
  CircularProgress,
  HStack,
  IconButton,
  Text,
  VStack,
} from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalContent,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { RadialButton } from "@components/radial-button";
import { useSocket } from "@utils/socket";
import { useRouter } from "next/navigation";

const LoadingModal = () => {
  const { task, updateUIState } = useTaskStore();
  const { emit } = useSocket();
  const router = useRouter();
  const isOpen =
    task.uiState.loadingTaskState !== LoadingTaskState.SUCCESS &&
    task.uiState.loadingTaskState !== null;

  const closeSession = async () => {
    emit("soft_close_task", {
      task_id: task.taskId,
    });
    router.push("/home");
    await closeTask();
  };

  const renderHeader = () => {
    switch (task.uiState.loadingTaskState) {
      case LoadingTaskState.LOADING:
        return (
          <Text fontSize="md">Loading and initializing repository...</Text>
        );
      case LoadingTaskState.ALLOCATING:
      case LoadingTaskState.INITIALIZING_SANDBOX:
        return <Text fontSize="md">Provisioning resources...</Text>;
      case LoadingTaskState.CLONING_REPO:
      case LoadingTaskState.INSTALLING_DEPS:
      case LoadingTaskState.INDEXING:
      case LoadingTaskState.BUILDING:
        return <Text fontSize="md">Preparing workspace...</Text>;
      case LoadingTaskState.ALREADY_CONNECTED:
        return (
          <Text fontSize="md" color="red.500">
            Task View Moved
          </Text>
        );
      case LoadingTaskState.ERROR:
        return (
          <Text fontSize="md" color="red.500">
            Error initializing repository.
          </Text>
        );
      default:
        return <Text fontSize="md">Retrieving repository info...</Text>;
    }
  };

  const renderBody = () => {
    switch (task.uiState.loadingTaskState) {
      case LoadingTaskState.LOADING:
      case LoadingTaskState.ALLOCATING:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Allocating compute
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.INITIALIZING_SANDBOX:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Initializing sandbox
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.INSTALLING_DEPS:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Installing dependencies
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.CLONING_REPO:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Cloning repository
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.INDEXING:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Indexing codebase (may take a minute)
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.BUILDING:
        return (
          <VStack
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <Text fontSize="xs" color="gray.400">
              Building repository
            </Text>
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </VStack>
        );
      case LoadingTaskState.ERROR:
        return (
          <VStack spacing={4} align="center" p={3}>
            <Text>
              An error occurred while loading the repository. Please ensure the
              project is working and try again.
            </Text>
            <HStack spacing={4}>
              <RadialButton
                colorScheme="red"
                leftIcon={ChevronLeftIcon}
                onClick={closeSession}
                maxW="300px"
                bg={["rgba(255, 100, 100, 1)", "rgba(200, 30, 30, 1)"]}
                border="1px solid rgba(225, 80, 80, 1)"
                boxShadow="none"
              >
                Go Back
              </RadialButton>
            </HStack>
          </VStack>
        );
      case LoadingTaskState.ALREADY_CONNECTED:
        return (
          <VStack spacing={4} align="center" p={3}>
            <Text>You opened this task elsewhere.</Text>
            <HStack spacing={4}>
              <RadialButton
                colorScheme="red"
                leftIcon={ChevronLeftIcon}
                onClick={closeSession}
                maxW="300px"
                bg={["rgba(255, 100, 100, 1)", "rgba(200, 30, 30, 1)"]}
                border="1px solid rgba(225, 80, 80, 1)"
                boxShadow="none"
              >
                Go Back
              </RadialButton>
            </HStack>
          </VStack>
        );
      default:
        return (
          <Box
            w="full"
            display="flex"
            justifyContent="center"
            alignItems="center"
            mb={4}
          >
            <CircularProgress
              isIndeterminate
              size="25px"
              color="blue.500"
              mx="auto"
            />
          </Box>
        );
    }
  };

  const openSettingsModal = () => {
    updateUIState({
      isWorkspaceSettingsModalOpen: true,
      workspaceSettingsPanelToShow: "settings",
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {}}
      closeOnOverlayClick={false}
      closeOnEsc={false}
    >
      <ModalOverlay />
      <ModalContent>
        <ModalHeader pl={3}>
          <HStack>
            <IconButton
              size="xs"
              icon={<ArrowBackIcon />}
              colorScheme="red"
              variant="outline"
              aria-label="Go Back"
              onClick={closeSession}
            />
            <IconButton
              size="xs"
              icon={<SettingsIcon />}
              colorScheme="blue"
              variant="outline"
              aria-label="Settings"
              onClick={openSettingsModal}
              mr={1}
            />
            {renderHeader()}
          </HStack>
        </ModalHeader>
        <ModalBody>{renderBody()}</ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default LoadingModal;
