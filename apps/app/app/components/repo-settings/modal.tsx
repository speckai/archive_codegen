"use client";

import { WorkspaceSettings } from "@ctypes/repos";

import { useTaskStore } from "@/app/utils/stores/task";
import { SettingsIcon } from "@chakra-ui/icons";
import { HStack, Icon, IconButton, Text, VStack } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { useAuth } from "@utils/auth";
import { getWorkspaceSettings } from "@utils/functions/repos";
import { useEffect, useState } from "react";
import { BsPersonWorkspace } from "react-icons/bs";
import { FaExternalLinkAlt, FaGithub } from "react-icons/fa";
import SettingsBody from "./body";

export default function RepoSettingsModal() {
  const { task, updateUIState } = useTaskStore();
  const { token } = useAuth();
  const [localSettings, setLocalSettings] = useState<WorkspaceSettings | null>(
    null,
  );
  const [savedSettings, setSavedSettings] = useState<WorkspaceSettings | null>(
    null,
  );

  const setMenuOpened = (opened: boolean) => {
    updateUIState({
      isWorkspaceSettingsModalOpen: opened,
      workspaceSettingsPanelToShow: "settings",
    });
  };

  async function fetchSettings() {
    const response = await getWorkspaceSettings(task.taskId!, token!);

    if (response.success && response.settings) {
      setLocalSettings(response.settings);
      setSavedSettings(response.settings);
    }
  }

  useEffect(() => {
    if (task.uiState.isWorkspaceSettingsModalOpen) {
      setLocalSettings(null);
      setSavedSettings(null);

      fetchSettings();
    }
  }, [task.uiState.isWorkspaceSettingsModalOpen]);

  return (
    <Modal
      isOpen={task.uiState.isWorkspaceSettingsModalOpen || false}
      onClose={() => {
        setMenuOpened(false);
      }}
      size="4xl"
      closeOnOverlayClick={!task.isInSettingsAgent}
    >
      <ModalOverlay />
      <ModalContent
        zIndex={1000}
        bg="rgba(0,0,0,0.3)"
        borderColor="rgba(255,255,255,0.2)"
      >
        <ModalHeader>
          <VStack align="left" spacing={2}>
            <Text fontSize="xl" display="flex" alignItems="center">
              <Icon as={SettingsIcon} boxSize={4} color="gray.300" mr={2} />
              Settings{" "}
            </Text>
            <HStack>
              <Icon as={FaGithub} boxSize={4} color="gray.400" />
              <Text fontSize="sm" color="gray.400" fontWeight="normal">
                {task.currentWorkspace?.repoFullName}
              </Text>
              <IconButton
                aria-label="Open external repo"
                icon={<FaExternalLinkAlt />}
                size="xs"
                variant="ghost"
                onClick={() =>
                  window.open(
                    task.currentWorkspace?.repoUrl,
                    "_blank",
                    "noopener,noreferrer",
                  )
                }
              />
            </HStack>
            <HStack>
              <Icon as={BsPersonWorkspace} boxSize={4} color="gray.400" />
              <Text fontSize="sm" color="gray.400" fontWeight="normal">
                {task.currentWorkspace?.workspaceName}
              </Text>
            </HStack>
          </VStack>
        </ModalHeader>
        {!task.isInSettingsAgent && <ModalCloseButton />}
        <ModalBody>
          <SettingsBody
            localSettings={localSettings}
            setLocalSettings={setLocalSettings}
            savedSettings={savedSettings}
            close={() => setMenuOpened(false)}
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
