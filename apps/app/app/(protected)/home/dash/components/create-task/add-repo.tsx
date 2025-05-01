import {
  Avatar,
  Box,
  Button,
  Checkbox,
  HStack,
  Icon,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Link,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
} from "@components/modal";
import { RadialButton } from "@components/radial-button";
import { Repo } from "@ctypes/repos";
import { useAuth } from "@utils/auth";
import { addInstalledRepos, getInstalledRepos } from "@utils/functions/repos";
import { useEffect, useState } from "react";
import { FaBook, FaChevronLeft } from "react-icons/fa";
import { FaGithub } from "react-icons/fa6";
import { FiExternalLink, FiRefreshCw, FiSearch } from "react-icons/fi";
import { MdLock, MdOutlinePublic } from "react-icons/md";

interface InstalledReposModalProps {
  isOpen: boolean;
  setMode: (mode: "task" | "addRepo") => void;
}

export default function InstalledReposModal({
  isOpen,
  setMode,
}: InstalledReposModalProps) {
  const { token } = useAuth();
  const toast = useToast();
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [installedRepos, setInstalledRepos] = useState<Repo[]>([]);
  const [selectedReposIds, setSelectedReposIds] = useState<string[]>([]);
  const [sendingAddedRepos, setSendingAddedRepos] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredRepos = searchTerm
    ? installedRepos.filter((repo) =>
        repo.fullName.toLowerCase().includes(searchTerm.toLowerCase()),
      )
    : installedRepos;

  const fetchInstalledRepos = async () => {
    setLoadingRepos(true);
    const result = await getInstalledRepos(token || "");

    if (result.success) {
      if (result.installedRepos) {
        const sortedRepos = result.installedRepos.sort(
          (a, b) => (b.lastOpenedUnix || 0) - (a.lastOpenedUnix || 0),
        );

        setInstalledRepos(sortedRepos);
      }
      if (result.failedInstallations && result.failedInstallations.length > 0) {
        toast({
          title: "Failed to fetch repos from accounts:",
          description: `${result.failedInstallations.join(", ")} -- Try reinstalling the app for the failed accounts.`,
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    }
    setLoadingRepos(false);
  };

  useEffect(() => {
    if (!isOpen || !token) {
      return;
    }

    setInstalledRepos([]);
    setSelectedReposIds([]);

    fetchInstalledRepos();
  }, [token, isOpen]);

  const handleRepoSelection = (repoId: string) => {
    setSelectedReposIds((prev) =>
      prev.includes(repoId)
        ? prev.filter((id) => id !== repoId)
        : [...prev, repoId],
    );
  };

  const handleSendAddedRepos = async () => {
    if (!token) {
      console.error("No token, can't add repos");
      return;
    }

    const selectedRepoIds = installedRepos
      .filter((repo) => selectedReposIds.includes(repo.gitRepoId.toString()))
      .map((repo) => repo.gitRepoId);

    setSendingAddedRepos(true);
    const result = await addInstalledRepos(selectedRepoIds, token);
    if (result.success) {
      setInstalledRepos(
        installedRepos.filter(
          (repo) => !selectedReposIds.includes(repo.gitRepoId.toString()),
        ),
      );
      setMode("task");
      toast({
        title: `Added ${result.addedRepos?.length || 0} repo${
          result.addedRepos?.length === 1 ? "" : "s"
        }`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
    } else {
      toast({
        title: "Error adding repos",
        description: result.message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
    setSendingAddedRepos(false);
  };

  const githubAppUrl = `https://github.com/apps/${
    process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "speck-engineer"
  }/installations/select_target`;

  return (
    <ModalContent>
      <ModalHeader>
        <HStack>
          <HStack>
            <IconButton
              aria-label="Close"
              icon={<FaChevronLeft />}
              onClick={() => setMode("task")}
              variant="outline"
              size="xs"
              colorScheme="red"
            />

            <Text>Add an installed repository</Text>
          </HStack>
          <ModalCloseButton />
        </HStack>
      </ModalHeader>
      <ModalBody>
        {loadingRepos ? (
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            py={4}
          >
            <Spinner size="lg" />
          </Box>
        ) : (
          <VStack align="start" overflow="auto" maxH="70vh" w="100%">
            {installedRepos.length > 5 && (
              <Box w="100%">
                <InputGroup size="sm" borderRadius="full">
                  <InputLeftElement pointerEvents="none">
                    <FiSearch color="gray.300" />
                  </InputLeftElement>
                  <Input
                    placeholder={`Search repositories...`}
                    value={searchTerm}
                    borderRadius="full"
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </InputGroup>
              </Box>
            )}

            <Table
              variant="simple"
              display={
                !loadingRepos && installedRepos.length > 0 ? "block" : "none"
              }
            >
              <Thead>
                <Tr>
                  <Th p={2}>
                    <IconButton
                      icon={<FiRefreshCw />}
                      onClick={fetchInstalledRepos}
                      isLoading={loadingRepos}
                      size="xs"
                      aria-label="Refresh repos"
                    >
                      Refresh Repos
                    </IconButton>
                  </Th>
                  <Th p={2} w="80%">
                    Name
                  </Th>
                  <Th p={2}>Link</Th>
                  <Th p={2} w="20%">
                    Last Updated
                  </Th>
                  <Th p={2}>Select</Th>
                </Tr>
              </Thead>
              <Tbody>
                {filteredRepos.map((repo) => (
                  <Tr key={repo.gitRepoId}>
                    <Td p={0} pr={2} textAlign="center">
                      <HStack spacing={2} pl={2}>
                        <Icon
                          as={
                            repo.visibility === "public"
                              ? MdOutlinePublic
                              : MdLock
                          }
                          color="gray.400"
                        />
                        <Avatar
                          src={repo.owner.avatarUrl}
                          size="xs"
                          borderRadius="full"
                        />
                      </HStack>
                    </Td>
                    <Td p={2}>{repo.fullName}</Td>
                    <Td p={2} textAlign="center">
                      <Link href={repo.url} isExternal>
                        <IconButton
                          aria-label="Open repo"
                          icon={<FiExternalLink size="1rem" />}
                          variant="ghost"
                          size="sm"
                        />
                      </Link>
                    </Td>
                    <Td p={2} textAlign="center">
                      {repo.lastOpenedUnix
                        ? new Date(
                            repo.lastOpenedUnix * 1000,
                          ).toLocaleDateString("en-US", {
                            month: "2-digit",
                            day: "2-digit",
                            year: "2-digit",
                          })
                        : "Never"}
                    </Td>
                    <Td p={2} textAlign="center">
                      <Checkbox
                        isChecked={selectedReposIds.includes(
                          repo.gitRepoId.toString(),
                        )}
                        onChange={() =>
                          handleRepoSelection(repo.gitRepoId.toString())
                        }
                      />
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
            <Button
              size="xs"
              variant="ghost"
              onClick={() => window.open(githubAppUrl, "_blank")}
              display={
                !loadingRepos && installedRepos.length > 0 ? "block" : "none"
              }
            >
              Add more
            </Button>
          </VStack>
        )}
        {!loadingRepos && installedRepos.length === 0 && (
          <VStack py={4} spacing={4}>
            <Text fontSize="md">
              You don't have any more repositories installed.
            </Text>
            <HStack spacing={6}>
              <Button
                as={Link}
                leftIcon={<FaGithub />}
                href={githubAppUrl}
                colorScheme="blue"
                rounded="full"
                size="sm"
                isExternal
              >
                Install Speck to more repos
              </Button>
              <Button
                as={Link}
                leftIcon={<FaBook />}
                href="https://docs.speck.sh/docs/installation"
                colorScheme="gray"
                rounded="full"
                size="sm"
                isExternal
              >
                Read the docs
              </Button>
            </HStack>
          </VStack>
        )}
      </ModalBody>
      <ModalFooter>
        <RadialButton
          onClick={handleSendAddedRepos}
          isDisabled={selectedReposIds.length === 0}
          isLoading={sendingAddedRepos}
          shouldPulse
        >
          Add {selectedReposIds.length} Repos
        </RadialButton>
      </ModalFooter>
    </ModalContent>
  );
}
