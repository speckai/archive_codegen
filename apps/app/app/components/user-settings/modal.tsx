"use client";

import { SettingsIcon } from "@chakra-ui/icons";
import { Icon, Text, VStack } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import UserSettingsBody from "./body";

interface UserSettingsModalProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}
export default function UserSettingsModal({
  isOpen,
  setIsOpen,
}: UserSettingsModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        setIsOpen(false);
      }}
    >
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <VStack align="left" spacing={1}>
            <Text fontSize="xl" display="flex" alignItems="center">
              <Icon as={SettingsIcon} boxSize={4} color="gray.300" mr={2} />
              User Settings
            </Text>
          </VStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <UserSettingsBody
            close={() => {
              setIsOpen(false);
            }}
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
