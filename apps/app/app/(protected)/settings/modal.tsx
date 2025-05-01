import { HStack, Text, VStack } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { RadialButton } from "@components/radial-button";
import { FaSave } from "react-icons/fa";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  changedFields: string[];
  onSave: () => void;
}

export function SettingsModal({
  isOpen,
  onClose,
  changedFields,
  onSave,
}: SettingsModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Confirm Changes</ModalHeader>
        <ModalBody>
          <VStack
            align="start"
            spacing={2}
            bg="rgba(255, 255, 255, 0.02)"
            p={4}
            borderRadius="lg"
            borderWidth={1}
            borderColor="rgba(255, 255, 255, 0.04)"
          >
            {changedFields.map((change, index) => (
              <Text key={index} fontSize="sm" color="gray.200" w="full">
                {change}
              </Text>
            ))}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack spacing={2}>
            <RadialButton
              onClick={onClose}
              bg={["rgba(255, 100, 100, 1)", "rgba(200, 30, 30, 1)"]}
              hoveredBg={["rgba(255, 100, 100, 0.3)", "rgba(200, 30, 30, 0.3)"]}
              border="1px solid rgba(255, 100, 100, 0.5)"
              boxShadow="none"
              size="sm"
            >
              Cancel
            </RadialButton>
            <RadialButton
              onClick={onSave}
              size="sm"
              boxShadow="none"
              rightIcon={FaSave}
              rightIconProps={{
                animatedMarginLeft: 8,
                size: "0.8rem",
              }}
              shouldPulse
            >
              Confirm
            </RadialButton>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
