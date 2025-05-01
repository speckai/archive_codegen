import { useTaskStore } from "@/app/utils/stores/task";
import { AddIcon, DeleteIcon } from "@chakra-ui/icons";
import {
  Box,
  Button,
  HStack,
  Input,
  Text,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  Popover,
  PopoverBody,
  PopoverContent,
  PopoverFooter,
  PopoverHeader,
  PopoverTrigger,
} from "@components/popover";
import { RadialButton } from "@components/radial-button";
import Editor from "@monaco-editor/react";
import { useAuth } from "@utils/auth";
import { getRuntimeFiles, saveRuntimeFiles } from "@utils/functions/repos";
import { useSocket } from "@utils/socket";
import { useEffect, useRef, useState } from "react";
import { FaSave } from "react-icons/fa";

export default function RuntimeFiles({ close }: { close: () => void }) {
  const [files, setFiles] = useState<{ name: string; contents: string }[]>([]);
  const [originalFiles, setOriginalFiles] = useState<
    { name: string; contents: string }[]
  >([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [editingFileName, setEditingFileName] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState("");
  const {
    isOpen: isDeleteOpen,
    onOpen: onDeleteOpen,
    onClose: onDeleteClose,
  } = useDisclosure();
  const {
    isOpen: isAddOpen,
    onOpen: onAddOpen,
    onClose: onAddClose,
  } = useDisclosure();
  const deleteRef = useRef<string | null>(null);
  const { token } = useAuth();
  const { task } = useTaskStore();
  const toast = useToast();
  const [hasChanges, setHasChanges] = useState(false);
  const { emit } = useSocket();

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchRuntimeFiles();
  }, [token]);

  const fetchRuntimeFiles = async () => {
    const response = await getRuntimeFiles(
      task.currentWorkspace?.gitRepoId || 0,
      token || "",
    );
    if (response.success) {
      setFiles(response.runtimeFiles || []);
      setOriginalFiles(response.runtimeFiles || []);
    } else {
      console.error("Failed to fetch runtime files:", response.message);
      toast({
        title: "Failed to fetch runtime files",
        description: response.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const saveRuntimeFilesFn = async () => {
    if (task.isInSettingsAgent) {
      emit("requested_runtime_files", {
        files: files,
      });
      close();
      return;
    }

    const response = await saveRuntimeFiles(
      task.currentWorkspace?.gitRepoId || 0,
      token || "",
      files,
    );
    if (response.success) {
      setOriginalFiles([...files]);
      setHasChanges(false);
      toast({
        title: "Runtime files saved successfully",
        status: "success",
        duration: 2000,
        isClosable: true,
      });
    } else {
      console.error("Failed to save runtime files:", response.message);
      toast({
        title: "Failed to save runtime files",
        description: response.message,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleFileSelect = (fileName: string) => {
    setSelectedFile(fileName);
    setEditingFileName(null);
  };

  const handleFileContentChange = (newContent: string | undefined) => {
    if (selectedFile && newContent) {
      const updatedFiles = files.map((file) =>
        file.name === selectedFile ? { ...file, contents: newContent } : file,
      );
      setFiles(updatedFiles);
      checkForChanges(updatedFiles);
    }
  };

  const handleFileNameEdit = (fileName: string) => {
    setEditingFileName(fileName);
  };

  const handleFileNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newName = event.target.value;
    const updatedFiles = files.map((file) =>
      file.name === editingFileName ? { ...file, name: newName } : file,
    );
    setFiles(updatedFiles);
    if (selectedFile === editingFileName) {
      setSelectedFile(newName);
    }
    setEditingFileName(null);
    checkForChanges(updatedFiles);
  };

  const handleDeleteFile = (fileName: string) => {
    deleteRef.current = fileName;
    onDeleteOpen();
  };

  const confirmDeleteFile = () => {
    if (deleteRef.current) {
      const updatedFiles = files.filter(
        (file) => file.name !== deleteRef.current,
      );
      setFiles(updatedFiles);
      if (selectedFile === deleteRef.current) {
        setSelectedFile(null);
      }
      onDeleteClose();
      checkForChanges(updatedFiles);
    }
  };

  const handleAddFile = () => {
    if (newFileName) {
      const updatedFiles = [...files, { name: newFileName, contents: "" }];
      setFiles(updatedFiles);
      setNewFileName("");
      onAddClose();
      checkForChanges(updatedFiles);
      setSelectedFile(newFileName);
    }
  };

  const checkForChanges = (
    updatedFiles: { name: string; contents: string }[],
  ) => {
    const hasChanges =
      JSON.stringify(updatedFiles) !== JSON.stringify(originalFiles);
    setHasChanges(hasChanges);
  };

  return (
    <Box>
      <VStack mb={4} alignItems="flex-start" spacing={0} p={0}>
        <Text fontSize="sm">
          Files to be injected into the project at runtime (example: .env files)
        </Text>
        <Text fontSize="xs" color="gray.400">
          Restart task to apply changes
        </Text>
      </VStack>
      <HStack alignItems="flex-start" spacing={0}>
        <VStack
          h="400px"
          overflowY="scroll"
          w="25%"
          alignItems="stretch"
          spacing={0}
          borderRight="1px solid rgba(255,255,255,0.2)"
        >
          {files.map((file) => (
            <Box key={file.name} position="relative">
              {editingFileName === file.name ? (
                <Input
                  value={file.name}
                  onChange={handleFileNameChange}
                  onBlur={() => setEditingFileName(null)}
                  autoFocus
                  size="sm"
                />
              ) : (
                <Button
                  onClick={() => handleFileSelect(file.name)}
                  onDoubleClick={() => handleFileNameEdit(file.name)}
                  variant={selectedFile === file.name ? "solid" : "outline"}
                  borderRadius="none"
                  size="sm"
                  justifyContent="space-between"
                  border="none"
                  w="100%"
                  position="relative"
                  _hover={{
                    "& > .delete-icon": {
                      opacity: 1,
                    },
                  }}
                >
                  <Text>{file.name}</Text>
                  <DeleteIcon
                    className="delete-icon"
                    opacity={0}
                    transition="opacity 0.2s"
                    color="red.300"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteFile(file.name);
                    }}
                  />
                </Button>
              )}
            </Box>
          ))}
          <Popover isOpen={isAddOpen} onClose={onAddClose}>
            <PopoverTrigger>
              <Button
                leftIcon={<AddIcon />}
                onClick={onAddOpen}
                variant="outline"
                borderRadius="none"
                size="sm"
                justifyContent="flex-start"
                border="none"
                w="100%"
              >
                Add File
              </Button>
            </PopoverTrigger>
            <PopoverContent bg="rgba(20, 25, 30, 0.9)">
              <PopoverHeader>Add New File</PopoverHeader>
              <PopoverBody>
                <Input
                  placeholder="Enter file name"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                />
              </PopoverBody>
              <PopoverFooter>
                <Button size="sm" onClick={handleAddFile}>
                  Add
                </Button>
              </PopoverFooter>
            </PopoverContent>
          </Popover>
        </VStack>
        <Box width="75%">
          {selectedFile ? (
            <Editor
              height="400px"
              language="plaintext"
              value={files.find((f) => f.name === selectedFile)?.contents}
              onChange={handleFileContentChange}
              theme="vs-dark"
            />
          ) : (
            <Text ml={6}>Select a file</Text>
          )}
        </Box>
      </HStack>
      <HStack justifyContent="flex-end" mt={4}>
        <RadialButton
          onClick={() => {
            emit("requested_runtime_files", {
              files: [],
            });
            close();
          }}
          isOutlined
          boxShadow="none"
          border="1px solid rgba(255,100,100,0.4)"
          size="sm"
        >
          Close
        </RadialButton>
        <RadialButton
          onClick={saveRuntimeFilesFn}
          isDisabled={!hasChanges}
          leftIcon={FaSave}
          size="sm"
        >
          Save Runtime Files
        </RadialButton>
      </HStack>
      <Popover isOpen={isDeleteOpen} onClose={onDeleteClose}>
        <PopoverContent bg="rgba(20, 25, 30, 0.9)">
          <PopoverHeader>Confirm Delete</PopoverHeader>
          <PopoverBody>Are you sure you want to delete this file?</PopoverBody>
          <PopoverFooter>
            <Button size="sm" onClick={onDeleteClose} mr={2}>
              Cancel
            </Button>
            <Button size="sm" colorScheme="red" onClick={confirmDeleteFile}>
              Delete
            </Button>
          </PopoverFooter>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
