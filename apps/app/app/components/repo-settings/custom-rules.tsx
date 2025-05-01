import { useTaskStore } from "@/app/utils/stores/task";
import {
  Box,
  Button,
  ModalCloseButton,
  Text,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { RadialButton } from "@components/radial-button";
import Editor, { DiffEditor } from "@monaco-editor/react";
import { useAuth } from "@utils/auth";
import {
  getRepoCustomRules,
  saveRepoCustomRules,
} from "@utils/functions/repos";
import { useEffect, useState } from "react";
import { FaSave } from "react-icons/fa";

export default function CustomRules() {
  const [rules, setRules] = useState<string>("");
  const [originalRules, setOriginalRules] = useState<string>("");
  const { token } = useAuth();
  const { task } = useTaskStore();
  const toast = useToast();
  const [hasChanges, setHasChanges] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchCustomRules();
  }, [token]);

  const fetchCustomRules = async () => {
    const response = await getRepoCustomRules(
      task.currentWorkspace?.gitRepoId || 0,
      token || "",
    );
    if (response.success) {
      setRules(response.rules || "");
      setOriginalRules(response.rules || "");
    } else {
      console.error("Failed to fetch custom rules:", response.message);
      toast({
        title: "Failed to fetch custom rules",
        description: response.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const saveCustomRules = async () => {
    const response = await saveRepoCustomRules(
      task.currentWorkspace?.gitRepoId || 0,
      token || "",
      rules,
    );
    if (response.success) {
      setOriginalRules(rules);
      setHasChanges(false);
      onClose();
      toast({
        title: "Custom rules saved successfully",
        status: "success",
        duration: 2000,
        isClosable: true,
      });
    } else {
      console.error("Failed to save custom rules:", response.message);
      toast({
        title: "Failed to save custom rules",
        description: response.message,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleRulesChange = (newContent: string | undefined) => {
    if (newContent !== undefined) {
      setRules(newContent);
      setHasChanges(newContent !== originalRules);
    }
  };

  return (
    <Box>
      <VStack mb={4} alignItems="flex-start" spacing={0} p={0}>
        <Text fontSize="sm">Custom rules for this repository</Text>
        <Text fontSize="xs" color="gray.400">
          Define custom rules for Speck to follow
        </Text>
      </VStack>
      <Box height="400px">
        <Editor
          height="100%"
          language="yaml"
          value={rules}
          onChange={handleRulesChange}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
          }}
        />
      </Box>
      <Box display="flex" justifyContent="flex-end" mt={4}>
        <RadialButton
          onClick={onOpen}
          isDisabled={!hasChanges}
          leftIcon={FaSave}
          size="sm"
        >
          Save Custom Rules
        </RadialButton>
      </Box>

      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent maxW="80vw">
          <ModalHeader>Confirm Changes</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text mb={4}>Review the changes before saving:</Text>
            <Box height="60vh">
              <DiffEditor
                height="100%"
                language="yaml"
                original={originalRules}
                modified={rules}
                theme="vs-dark"
                options={{
                  renderSideBySide: true,
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
              />
            </Box>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <RadialButton onClick={saveCustomRules} leftIcon={FaSave}>
              Confirm & Save
            </RadialButton>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
