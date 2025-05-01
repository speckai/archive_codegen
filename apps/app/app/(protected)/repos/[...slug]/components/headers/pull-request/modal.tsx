"use client";

import { TaskState } from "@/app/types/task";
import { useTaskStore } from "@/app/utils/stores/task";
import { HStack, Icon, ModalFooter, Text } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { useAuth } from "@utils/auth";
import { useState } from "react";
import { FaExclamationTriangle } from "react-icons/fa";
import PullRequest from "./pull-request";

interface PullRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PullRequestModal({
  isOpen,
  onClose,
}: PullRequestModalProps) {
  const { token } = useAuth();
  const { task } = useTaskStore();
  const [canClose, setCanClose] = useState(true);

  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={false}>
      <ModalOverlay />
      <ModalContent bg="rgba(50,50,50,0.3)">
        <ModalHeader>Create Pull Request</ModalHeader>
        <ModalCloseButton />
        <ModalBody p={4}>
          <PullRequest token={token || ""} isOpen={isOpen} onClose={onClose} />
        </ModalBody>
        {task &&
          task.taskState > TaskState.IDLE &&
          task.taskState < TaskState.DONE && (
            <ModalFooter pt={0}>
              <HStack alignItems="center" spacing={4}>
                <Icon as={FaExclamationTriangle} color="orange.400" />

                <Text fontSize="sm" color="orange.400">
                  <b>WARNING:</b> A task is in progress. You should wait until
                  it is done to save your changes.
                </Text>
              </HStack>
            </ModalFooter>
          )}
      </ModalContent>
    </Modal>
  );
}
