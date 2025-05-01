"use client";

import {
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
} from "@/app/components/modal";
import { ChevronRightIcon, ExternalLinkIcon } from "@chakra-ui/icons";
import {
  Avatar,
  Box,
  Breadcrumb,
  BreadcrumbItem,
  Button,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  Input,
  List,
  ListItem,
  NumberInput,
  NumberInputField,
  Select,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { RadialButton } from "@components/radial-button";
import { AnimatePresence, motion } from "framer-motion";
import { CiSettings } from "react-icons/ci";
import {
  RiAddLine,
  RiArrowLeftLine,
  RiFolderLine,
  RiGitBranchLine,
  RiGitRepositoryCommitsLine,
} from "react-icons/ri";

import { requestNewTask } from "@/app/utils/functions/task";
import { Repo, WorkspaceOption, WorkspaceType } from "@ctypes/repos";
import { useAuth } from "@utils/auth";
import { getAddedRepos } from "@utils/functions/repos";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface IssueDetails {
  title: string;
  description: string;
  number: number;
  state: string;
  url: string;
  repository: {
    id: number;
    name: string;
    owner: string;
  };
}

interface CreateTaskProps {
  setIsOpen: (isOpen: boolean) => void;
  setMode: (mode: "task" | "addRepo") => void;
  issueDetails?: IssueDetails | null;
}

interface SpaceSettingsType {
  branch: string;
  rootDirectory: string;
  packageManager: string;
  installCommand: string;
  devCommand: string;
  port: string;
}

// New settings view component
function SpaceSettingsView({
  selectedRepo,
  onBack,
  onSave,
  isLoading,
}: {
  selectedRepo: Repo | null;
  onBack: () => void;
  onSave: (settings: SpaceSettingsType) => void;
  isLoading: boolean;
}) {
  const { token } = useAuth();
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);
  const [subdirectories, setSubdirectories] = useState<string[]>([]);
  const [loadedRepoDetails, setLoadedRepoDetails] = useState(false);
  const [settings, setSettings] = useState<SpaceSettingsType>({
    branch: "main",
    rootDirectory: "/",
    packageManager: "npm",
    installCommand: "",
    devCommand: "",
    port: "",
  });

  useEffect(() => {
    // Update parent settings any time our settings change
    onSave(settings);
  }, [settings, onSave]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const fetchBranches = async () => {
      if (selectedRepo?.gitRepoId) {
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/github/get_repo_details/${selectedRepo.gitRepoId}`,
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            },
          );
          const result = await response.json();
          console.log(result);
          const { success, branch_names: branchNames, subdirectories } = result;
          if (success) {
            setLoadedRepoDetails(true);
            setAvailableBranches(branchNames);
            if ("main" in subdirectories) {
              setSettings((prev) => ({
                ...prev,
                branch: "main",
              }));
            }
            setSubdirectories(subdirectories);
            if ("/" in subdirectories) {
              setSettings((prev) => ({
                ...prev,
                rootDirectory: "/",
              }));
            }
          }
        } catch (error) {
          console.error("Error fetching branches:", error);
        }
      }
    };
    fetchBranches();
  }, [selectedRepo, token]);

  const handleChange = (field: keyof SpaceSettingsType, value: string) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <VStack align="stretch" spacing={6} pt={2} pb={4}>
      <HStack justify="space-between">
        <Button
          leftIcon={<RiArrowLeftLine />}
          variant="outline"
          size="sm"
          onClick={onBack}
        >
          Back
        </Button>
        <Text fontSize="lg" fontWeight="medium">
          Create new space for{" "}
          <Text as="span" fontWeight="bold" color="blue.300">
            {selectedRepo?.name}
          </Text>
        </Text>
      </HStack>

      <VStack align="stretch" spacing={4}>
        <FormControl>
          <HStack>
            <FormLabel>
              Branch {!loadedRepoDetails && <Spinner size="xs" ml={3} />}
            </FormLabel>
          </HStack>
          <Select
            value={settings.branch}
            onChange={(e) => handleChange("branch", e.target.value)}
            isDisabled={!loadedRepoDetails}
          >
            {availableBranches.map((branch) => (
              <option key={branch} value={branch}>
                {branch}
              </option>
            ))}
          </Select>
        </FormControl>

        <FormControl>
          <HStack>
            <FormLabel>
              Subdirectory {!loadedRepoDetails && <Spinner size="xs" ml={3} />}
            </FormLabel>
          </HStack>
          <Select
            value={settings.rootDirectory}
            onChange={(e) => handleChange("rootDirectory", e.target.value)}
            // placeholder={loadedRepoDetails ? "/" : "Loading..."}
            isDisabled={!loadedRepoDetails}
          >
            {subdirectories.map((subdirectory) => (
              <option key={subdirectory} value={subdirectory}>
                {subdirectory}
              </option>
            ))}
          </Select>
        </FormControl>

        <FormControl>
          <FormLabel>Package Manager</FormLabel>
          <Select
            value={settings.packageManager}
            onChange={(e) => handleChange("packageManager", e.target.value)}
          >
            <option value="npm">npm</option>
            <option value="yarn">yarn</option>
            <option value="pnpm">pnpm</option>
            <option value="bun">bun</option>
          </Select>
        </FormControl>

        <FormControl>
          <FormLabel>Install Command</FormLabel>
          <Input
            value={settings.installCommand}
            onChange={(e) => handleChange("installCommand", e.target.value)}
            placeholder="npm install"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Dev Command</FormLabel>
          <Input
            value={settings.devCommand}
            onChange={(e) => handleChange("devCommand", e.target.value)}
            placeholder="npm run dev"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Port</FormLabel>
          <NumberInput min={1} max={65535}>
            <NumberInputField
              value={settings.port}
              onChange={(e) => handleChange("port", e.target.value)}
              placeholder="3000"
            />
          </NumberInput>
        </FormControl>
      </VStack>

      {/* Mobile-only button - desktop uses footer */}
      <Box pt={4} display={{ base: "block", md: "none" }}>
        <Button
          onClick={() => onSave(settings)}
          colorScheme="blue"
          width="100%"
          isLoading={isLoading}
        >
          Create Space
        </Button>
      </Box>
    </VStack>
  );
}

// Repository and space selection view component
function SelectRepositoryAndSpaceView({
  repositories,
  selectedRepo,
  setSelectedRepo,
  selectedWorkspace,
  setSelectedWorkspace,
  issueDetails,
  setMode,
  onWorkspaceSetup,
}: {
  repositories: Repo[];
  selectedRepo: Repo | null;
  setSelectedRepo: (repo: Repo) => void;
  selectedWorkspace: WorkspaceOption | null;
  setSelectedWorkspace: (workspace: WorkspaceOption | null) => void;
  issueDetails: IssueDetails | null;
  setMode: (mode: "task" | "addRepo") => void;
  onWorkspaceSetup: () => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  const handleRepoClick = (repo: Repo) => {
    setSelectedRepo(repo);
    setSelectedWorkspace(null); // Reset selected space when changing repos
  };

  const handleSpaceClick = (space: WorkspaceOption) => {
    setSelectedWorkspace(space);
  };

  const handleNewSpaceClick = () => {
    if (selectedRepo) {
      setSelectedWorkspace({
        type: WorkspaceType.NEW,
      });
    }
  };

  return (
    <HStack align="flex-start" h="500px" spacing={0} position="relative">
      <HStack spacing={8} align="start" flex={1} h="full">
        <VStack flex={1} align="stretch" spacing={4}>
          <HStack justify="space-between">
            <Text fontSize="lg" fontWeight="medium" color="gray.200">
              Repositories
            </Text>
            <Button
              onClick={() => setMode("addRepo")}
              size="xs"
              colorScheme="blue"
              variant="outline"
            >
              Add Repository
            </Button>
          </HStack>
          <List spacing={0} borderRadius="md" overflow="hidden">
            {repositories.map((repo, index) => (
              <ListItem
                key={repo.name}
                onClick={() => handleRepoClick(repo)}
                p={3}
                cursor="pointer"
                transition="all 0.2s"
                borderLeft="1px"
                borderRight="1px"
                borderBottom="1px dashed"
                borderTop="1px dashed"
                borderColor={
                  selectedRepo?.name === repo.name
                    ? "blue.500"
                    : "rgba(255,255,255,0.1)"
                }
                borderTopRadius={index === 0 ? "md" : 0}
                borderBottomRadius={
                  index === repositories.length - 1 ? "md" : 0
                }
                _hover={{
                  bg: "whiteAlpha.100",
                }}
                _first={{
                  borderTop: "1px solid",
                  borderTopColor:
                    selectedRepo?.name === repo.name
                      ? "blue.500"
                      : "rgba(255,255,255,0.1)",
                }}
                _last={{
                  borderTop:
                    selectedRepo?.name === repo.name && repositories.length > 1
                      ? "1px dashed"
                      : "1px solid",
                  borderTopColor:
                    selectedRepo?.name === repo.name
                      ? "blue.500"
                      : repositories.length === 1
                        ? "rgba(255,255,255,0.1)"
                        : "rgba(255,255,255,0)",

                  borderBottom: "1px solid",
                  borderBottomColor:
                    selectedRepo?.name === repo.name
                      ? "blue.500"
                      : "rgba(255,255,255,0.1)",
                }}
                bg={
                  selectedRepo?.name === repo.name
                    ? "rgba(255, 255, 255, 0.1)"
                    : "transparent"
                }
              >
                <HStack spacing={3} width="100%" justifyContent="space-between">
                  <HStack spacing={3}>
                    <Avatar
                      size="sm"
                      name={repo.owner.name}
                      src={repo.owner.avatarUrl}
                    />
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="medium">{repo.name}</Text>
                      <Text fontSize="sm" color="gray.500">
                        {repo.owner.name}
                      </Text>
                    </VStack>
                  </HStack>

                  {/* Display issue info if this repo matches the issue's repository */}
                  {issueDetails &&
                    issueDetails.repository.id === repo.gitRepoId && (
                      <HStack spacing={1} ml="auto">
                        <VStack align="end" spacing={0}>
                          <Text fontSize="xs" color="blue.300">
                            Using Issue #{issueDetails.number}
                          </Text>
                          <Text
                            fontSize="xs"
                            color="gray.400"
                            noOfLines={1}
                            maxW="150px"
                          >
                            {issueDetails.title.length > 20
                              ? `${issueDetails.title.substring(0, 20)}...`
                              : issueDetails.title}
                          </Text>
                          <Button
                            as="a"
                            href={issueDetails.url}
                            target="_blank"
                            size="xs"
                            variant="ghost"
                            colorScheme="blue"
                            rightIcon={<ExternalLinkIcon />}
                            height="20px"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View on GitHub
                          </Button>
                        </VStack>
                      </HStack>
                    )}
                </HStack>
              </ListItem>
            ))}
          </List>
        </VStack>
        <Box w="1px" h="full" py={12} bg="rgba(255,255,255,0.05)" />
        <VStack flex={1} align="stretch" spacing={4} h="full">
          <Text fontSize="lg" fontWeight="medium" color="gray.200">
            Spaces
          </Text>
          {selectedRepo ? (
            <VStack
              align="stretch"
              spacing={3}
              p={4}
              overflowY="scroll"
              h="full"
            >
              {selectedRepo.workspaces.map((workspace) => (
                <motion.div
                  key={workspace.name}
                  style={{
                    width: "100%",
                    borderRadius: "full",
                  }}
                  initial={false}
                  animate={{
                    background:
                      selectedWorkspace?.name === workspace.name
                        ? "linear-gradient(to right, rgba(100, 150, 255, 0.2), rgba(50, 100, 255, 0))"
                        : "linear-gradient(to right, rgba(150, 150, 150, 0.2), rgba(150, 150, 150, 0))",
                  }}
                  transition={{
                    duration: 0.1,
                    ease: "circOut",
                  }}
                >
                  <Box
                    onClick={() => handleSpaceClick(workspace)}
                    cursor="pointer"
                    p={4}
                    borderRightRadius="md"
                    border="1px solid"
                    borderLeftWidth={
                      selectedWorkspace?.name === workspace.name ? 4 : 2
                    }
                    borderColor={
                      selectedWorkspace?.name === workspace.name
                        ? "rgba(50,100,255,0.2)"
                        : "rgba(255,255,255,0.05)"
                    }
                    borderLeftColor={
                      selectedWorkspace?.name === workspace.name
                        ? "rgba(50,150,255,0.3)"
                        : "rgba(255,255,255,0.05)"
                    }
                    transition="all 0.1s"
                    _hover={{
                      borderColor: "rgba(255,255,255,0.1)",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                  >
                    <VStack align="start" spacing={2}>
                      <Text fontWeight="medium" color="gray.200">
                        {workspace.name}
                      </Text>
                      <Divider opacity={0.1} />
                      <HStack spacing={4} fontSize="sm" color="gray.300">
                        <HStack spacing={1.5}>
                          <RiGitBranchLine size={14} />
                          <Text>{workspace.settings?.branch}</Text>
                        </HStack>
                        <HStack spacing={1.5}>
                          <RiFolderLine size={14} />
                          <Text>{workspace.settings?.rootDirectory}</Text>
                        </HStack>
                      </HStack>
                      <VStack
                        align="start"
                        spacing={1}
                        fontSize="xs"
                        color="gray.500"
                        pt={1}
                      >
                        <HStack>
                          <Text fontWeight="medium">Package Manager:</Text>
                          <Text>{workspace.settings?.packageManager}</Text>
                        </HStack>
                        <HStack>
                          <Text fontWeight="medium">Dev Command:</Text>
                          <Text>{workspace.settings?.devCommand}</Text>
                        </HStack>
                        <HStack>
                          <Text fontWeight="medium">Install Command:</Text>
                          <Text>{workspace.settings?.installCommand}</Text>
                        </HStack>
                        <HStack>
                          <Text fontWeight="medium">Port:</Text>
                          <Text>{workspace.settings?.port}</Text>
                        </HStack>
                      </VStack>
                    </VStack>
                  </Box>
                </motion.div>
              ))}
              <motion.div
                style={{ width: "100%" }}
                animate={{
                  height:
                    isHovered || selectedWorkspace?.type === WorkspaceType.NEW
                      ? "80px"
                      : "40px",
                }}
                transition={{ duration: 0.2 }}
              >
                <Button
                  size="sm"
                  variant="ghost"
                  w="full"
                  h="full"
                  borderRadius="md"
                  border="1px dashed"
                  borderColor={
                    selectedWorkspace?.type === WorkspaceType.NEW
                      ? "blue.400"
                      : "rgba(255,255,255,0.05)"
                  }
                  bg={
                    selectedWorkspace?.type === WorkspaceType.NEW
                      ? "whiteAlpha.200"
                      : "transparent"
                  }
                  _hover={{
                    bg: "whiteAlpha.50",
                    borderColor: "blue.400",
                  }}
                  onMouseEnter={() => setIsHovered(true)}
                  onMouseLeave={() => setIsHovered(false)}
                  onClick={handleNewSpaceClick}
                >
                  <VStack spacing={2} py={4}>
                    <HStack spacing={1}>
                      <RiAddLine />
                      <Text>New</Text>
                    </HStack>
                    <AnimatePresence>
                      {(isHovered ||
                        selectedWorkspace?.type === WorkspaceType.NEW) && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <VStack spacing={1} align="center">
                            <Text
                              fontSize="sm"
                              fontWeight="light"
                              color="gray.400"
                            >
                              Setup new space
                            </Text>
                          </VStack>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </VStack>
                </Button>
              </motion.div>
            </VStack>
          ) : (
            <VStack p={4} justify="center" h="full">
              <Text color="gray.500" fontSize="sm">
                Select a repository to view available spaces
              </Text>
            </VStack>
          )}
        </VStack>
      </HStack>
    </HStack>
  );
}

export default function CreateTaskBody({
  setIsOpen,
  setMode,
  issueDetails = null,
}: CreateTaskProps) {
  const { token } = useAuth();
  const [repositories, setRepositories] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] =
    useState<WorkspaceOption | null>(null);
  const router = useRouter();
  const [isLoadingTask, setIsLoadingTask] = useState(false);
  const [view, setView] = useState<"select" | "settings">("select");
  const [spaceSettings, setSpaceSettings] = useState<SpaceSettingsType>({
    branch: "main",
    rootDirectory: "/",
    packageManager: "npm",
    installCommand: "npm install",
    devCommand: "npm run dev",
    port: "3000",
  });

  const handleCreateClick = async () => {
    if (!selectedRepo || !selectedWorkspace || !token) {
      return;
    }

    if (selectedWorkspace.type === WorkspaceType.NEW && view === "select") {
      setView("settings");
      return;
    }

    setIsLoadingTask(true);

    const spaceName =
      selectedWorkspace.type === WorkspaceType.NEW
        ? "new-space"
        : selectedWorkspace.name || "new-space";

    // TODO: We need to modify the API to accept workspace settings
    const { success, message, taskId } = await requestNewTask(
      selectedRepo.gitRepoId,
      spaceName,
      issueDetails?.number,
      token,
    );

    if (!success || !taskId) {
      console.error("Failed to get task ID");
      console.error(message);
      setIsLoadingTask(false);
      return;
    }

    router.push(`/repos/${taskId}`);
    setIsOpen(false);
    setIsLoadingTask(false);
  };

  const handleSettingsSave = (settings: SpaceSettingsType) => {
    setSpaceSettings(settings);
  };

  const areSettingsValid = () => {
    if (selectedWorkspace?.type !== WorkspaceType.NEW) {
      return true;
    }

    return (
      selectedRepo?.gitRepoId &&
      spaceSettings.branch &&
      spaceSettings.rootDirectory &&
      spaceSettings.packageManager &&
      spaceSettings.installCommand &&
      spaceSettings.devCommand &&
      spaceSettings.port
    );
  };

  useEffect(() => {
    if (!token) {
      return;
    }

    const fetchRepos = async () => {
      const result = await getAddedRepos(token);
      if (result.success) {
        setRepositories(result.addedRepos || []);
      }
    };
    fetchRepos();
  }, [token]);

  useEffect(() => {
    if (issueDetails) {
      const matchingRepo = repositories.find(
        (repo) => repo.gitRepoId === issueDetails.repository.id,
      );
      if (matchingRepo) {
        setSelectedRepo(matchingRepo);
      }
    }
  }, [issueDetails, repositories]);

  return (
    <ModalContent>
      <ModalHeader>Create Task</ModalHeader>
      <ModalBody>
        {view === "select" ? (
          <SelectRepositoryAndSpaceView
            repositories={repositories}
            selectedRepo={selectedRepo}
            setSelectedRepo={setSelectedRepo}
            selectedWorkspace={selectedWorkspace}
            setSelectedWorkspace={setSelectedWorkspace}
            issueDetails={issueDetails}
            setMode={setMode}
            onWorkspaceSetup={() => setView("settings")}
          />
        ) : (
          <SpaceSettingsView
            selectedRepo={selectedRepo}
            onBack={() => setView("select")}
            onSave={handleSettingsSave}
            isLoading={isLoadingTask}
          />
        )}
      </ModalBody>
      <ModalFooter mt={4}>
        <HStack
          position="absolute"
          bottom={0}
          left={0}
          right={0}
          justify="space-between"
          align="center"
          px={4}
          py={2}
          borderTop="1px solid"
          borderColor="rgba(255,255,255,0.05)"
        >
          <Breadcrumb
            spacing="8px"
            separator={<ChevronRightIcon color="gray.500" />}
          >
            <BreadcrumbItem>
              <HStack>
                <RiGitRepositoryCommitsLine />
                <Text>{selectedRepo?.name || "Select Repository"}</Text>
                {selectedRepo &&
                  issueDetails &&
                  issueDetails.repository.id === selectedRepo.gitRepoId && (
                    <Text color="blue.300" fontSize="sm" mt={0.5}>
                      (Issue #{issueDetails.number})
                    </Text>
                  )}
              </HStack>
            </BreadcrumbItem>
            {selectedWorkspace && (
              <BreadcrumbItem>
                <HStack>
                  <CiSettings />
                  <Text>
                    {selectedWorkspace?.type === WorkspaceType.NEW
                      ? "New Space"
                      : selectedWorkspace?.name}
                  </Text>
                </HStack>
              </BreadcrumbItem>
            )}
          </Breadcrumb>

          <RadialButton
            onClick={handleCreateClick}
            isDisabled={
              !selectedRepo || !selectedWorkspace || !areSettingsValid()
            }
            isLoading={isLoadingTask}
            shouldPulse
          >
            {view === "settings"
              ? "Create"
              : selectedWorkspace?.type === WorkspaceType.NEW
                ? "Setup"
                : selectedRepo &&
                    issueDetails &&
                    issueDetails.repository.id === selectedRepo.gitRepoId
                  ? "Open Issue"
                  : "Create"}
          </RadialButton>
        </HStack>
      </ModalFooter>
    </ModalContent>
  );
}
