"use client";

import {
  Box,
  Button,
  HStack,
  Image,
  Skeleton,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { useAuth } from "@utils/auth";
import { getIsSubscribed } from "@utils/functions/billing";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AddDirectory from "./init-options-popover";

import { Avatar, Menu } from "@chakra-ui/react";
import RightClickMenu from "./right-click-menu";

import { deleteTask } from "@/app/utils/functions/task";
import { ChevronRightIcon, ExternalLinkIcon } from "@chakra-ui/icons";
import { RadialButton } from "@components/radial-button";
import { RiFolderLine, RiGithubFill } from "react-icons/ri";
import StatusTag from "./status-tag";

interface TaskStatus {
  taskId: string;
  owner: { image: string; name: string; avatarUrl: string; url: string };
  title: string;
  workspaceName: string;
  repoName: string;
  lastActionTimeUnix: number;
  taskStatus: string;
  gitRepoId: number;
  prNumber?: number;
  issueNumber?: number;
  issueClosed?: boolean;
}

export default function RepoTable() {
  const { token } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [rightClickedTask, setRightClickedTask] = useState<TaskStatus | null>(
    null,
  );
  const [fetchingTasks, setFetchingTasks] = useState<boolean>(true);
  const [openingTaskId, setOpeningTaskId] = useState<string | null>(null);
  const [isSubscribed, setIsSubscribed] = useState<boolean | null>(null);
  const [loadingSubscription, setLoadingSubscription] = useState<boolean>(true);
  const [lastAmountTasks, setLastAmountTasks] = useState<number>(0);
  const [tasks, setTasks] = useState<TaskStatus[]>([]);
  const toast = useToast();

  const formatTimestamp = (timestamp: number | null): string => {
    if (!timestamp) {
      return "Never";
    }
    const now = Date.now();
    const diff = now - timestamp * 1000; // Remove the * 1000 conversion

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days} day${days > 1 ? "s" : ""} ago`;
    } else if (hours > 0) {
      return `${hours} hour${hours > 1 ? "s" : ""} ago`;
    } else if (minutes > 0) {
      return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
    } else {
      return "Just now";
    }
  };

  const handleContextMenu = (
    event: React.MouseEvent<HTMLDivElement>,
    task: TaskStatus,
  ) => {
    event.preventDefault();
    setMenuPosition({ x: event.clientX, y: event.clientY });
    setMenuOpen(true);
    setRightClickedTask(task);
  };

  const openTask = (task: TaskStatus | null) => {
    if (!task) {
      return;
    }

    setOpeningTaskId(task.taskId);
    router.push(`/repos/${task.taskId}`);
  };

  const deleteTaskOp = async (task: TaskStatus | null) => {
    if (!task || !token) {
      return;
    }

    const result = await deleteTask(task.gitRepoId, task.taskId, token);

    if (result.success) {
      toast({
        title: "Task deleted",
        description: `Successfully deleted task`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      fetchTasks();
    } else {
      toast({
        title: "Error deleting task",
        description: "Failed to delete the task. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const fetchTasks = async () => {
    if (token) {
      setFetchingTasks(true);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/tasks/get`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );
        const data = await response.json();
        if (data.success) {
          const transformedTasks = data.tasks.map((task: any) => ({
            taskId: task.task_id,
            owner: {
              avatarUrl: task.owner.avatar_url,
              name: task.owner.name,
              url: task.owner.url,
            },
            title: task.title,
            workspaceName: task.workspace_name,
            repoName: task.repo_name,
            lastActionTimeUnix: task.last_action_time_unix,
            taskStatus: task.task_status,
            gitRepoId: task.git_repo_id,
            prNumber: task.pr_number,
            issueNumber: task.issue_number,
            issueClosed: task.issue_closed,
          }));
          transformedTasks.sort(
            (a: TaskStatus, b: TaskStatus) =>
              b.lastActionTimeUnix - a.lastActionTimeUnix,
          );
          setTasks(transformedTasks);
        }
      } catch (error) {
        console.error("Error fetching tasks:", error);
      } finally {
        setFetchingTasks(false);
      }
    }
  };

  useEffect(() => {
    const lastAmountTasks = localStorage.getItem("lastAmountTasks");
    if (lastAmountTasks) {
      setLastAmountTasks(parseInt(lastAmountTasks));
    }
    setTasks([]);

    if (!token || loadingSubscription) {
      return;
    }

    fetchTasks();
  }, [token, loadingSubscription]);

  useEffect(() => {
    if (!token) {
      return;
    }
    const checkSubscription = async () => {
      setLoadingSubscription(true);
      const isSubscribed = await getIsSubscribed(token);
      setIsSubscribed(isSubscribed);
      setLoadingSubscription(false);
    };
    checkSubscription();
  }, [token]);

  return (
    <>
      <TableContainer
        border="1px"
        borderRadius="lg"
        borderColor="rgba(255, 255, 255, 0.2)"
        w="full"
        minH="90vh"
        position="relative"
        onContextMenu={(e) => {
          const isClickOnRepo = (e.target as HTMLElement).closest(
            "tr[data-repo-id]",
          );
          if (!isClickOnRepo && menuOpen) {
            setMenuOpen(false);
          }
        }}
      >
        {!isSubscribed && !loadingSubscription && (
          <Box
            position="absolute"
            top="0"
            left="0"
            right="0"
            bottom="0"
            bg="rgba(10, 10, 10, 0.5)"
            zIndex="1"
            display="flex"
            alignItems="center"
            justifyContent="center"
            borderRadius="lg"
          >
            <VStack spacing={4}>
              <Box
                as={motion.div}
                animate={{
                  y: [0, 0, 0],
                  transition: {
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeOut",
                    times: [0, 0.5, 1],
                  },
                }}
                mb={2}
              >
                <Image
                  src="/logos/no-bg/speck-logo-512.webp"
                  alt="Speck Logo"
                  width={50}
                  height={50}
                  opacity={0.8}
                  filter="drop-shadow(0 0 15px rgba(40, 80, 255, 0.7))"
                />
              </Box>
              <Text color="white" fontSize="lg">
                You don't have an active subscription! Subscribe to Speck to
                continue.
              </Text>
              <RadialButton
                onClick={() => router.push("/settings")}
                shouldPulse
              >
                Subscribe
              </RadialButton>
            </VStack>
          </Box>
        )}

        {/* Desktop View */}
        <Box display={{ base: "none", md: "block" }} w="full">
          <Table variant="simple" size="md" w="full">
            <Thead>
              <Tr>
                <Th
                  w="40%"
                  padding="8px 16px"
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Name
                </Th>
                <Th
                  w="30%"
                  padding="8px 16px"
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    textAlign: "left",
                  }}
                >
                  Last Action
                </Th>
                <Th
                  w="20%"
                  padding="8px 16px"
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    textAlign: "left",
                  }}
                >
                  Status
                </Th>
                <Th
                  w="20%"
                  padding="8px 16px"
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.2)",
                    fontSize: "12px",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  <HStack justify="flex-end" my={0}>
                    <AddDirectory shouldPulse={tasks.length === 0} />
                  </HStack>
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {fetchingTasks &&
                Array.from({ length: lastAmountTasks }).map((_, i) => (
                  <Tr key={i}>
                    <Td>
                      <Skeleton h="30px" />
                    </Td>
                    <Td>
                      <Skeleton h="30px" />
                    </Td>
                    <Td>
                      <Skeleton h="30px" />
                    </Td>
                    <Td>
                      <Skeleton h="30px" />
                    </Td>
                  </Tr>
                ))}

              {tasks.map((task: TaskStatus, index: number) => (
                <motion.tr
                  key={`desktop-${task.taskId}`}
                  data-repo-id={task.taskId}
                  style={{
                    height: "50px",
                  }}
                  initial={{ opacity: 0 }}
                  animate={{
                    opacity: 1,
                    transition: {
                      delay: 0.05 * index,
                    },
                  }}
                  whileHover={{
                    backgroundColor: "rgba(25, 100, 255, 0.075)",
                    transition: {
                      duration: 0.1,
                    },
                  }}
                  onContextMenu={(e: React.MouseEvent<HTMLTableRowElement>) =>
                    handleContextMenu(e, task)
                  }
                >
                  <Td
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                      padding: "10px",
                      paddingLeft: "15px",
                    }}
                  >
                    <HStack spacing={4} align="center">
                      <Tooltip label={task.owner.name}>
                        <Avatar
                          size="xs"
                          src={task.owner.avatarUrl}
                          name={task.owner.name}
                        />
                      </Tooltip>
                      <VStack align="start" spacing={1} p={1}>
                        <Text fontWeight="medium">{task.title}</Text>
                        <Box fontSize="sm" color="gray.500">
                          <HStack spacing={2} alignItems="center">
                            <HStack spacing={1} alignItems="center">
                              <RiFolderLine size={12} />
                              <Text as="span">{task.workspaceName}</Text>
                            </HStack>
                            <Text as="span" color="gray.400">
                              •
                            </Text>
                            <HStack spacing={1} alignItems="center">
                              <RiGithubFill size={12} />
                              <Text as="span">{task.repoName}</Text>
                            </HStack>
                            {task.issueNumber && (
                              <>
                                <Button
                                  as="a"
                                  href={`https://github.com/${task.owner.name}/${task.repoName}/issues/${task.issueNumber}`}
                                  target="_blank"
                                  size="xs"
                                  variant="ghost"
                                  colorScheme={
                                    task.issueClosed === true
                                      ? "purple"
                                      : "blue"
                                  }
                                  rightIcon={<ExternalLinkIcon boxSize={3} />}
                                  height="18px"
                                  minW="auto"
                                  px={1}
                                  mt={0.5}
                                  onClick={(e) => e.stopPropagation()}
                                  fontWeight="normal"
                                >
                                  Issue #{task.issueNumber}
                                </Button>
                              </>
                            )}
                          </HStack>
                        </Box>
                      </VStack>
                    </HStack>
                  </Td>
                  <Td
                    color="gray.500"
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                    }}
                  >
                    {formatTimestamp(task.lastActionTimeUnix)}
                  </Td>
                  <Td
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                      textAlign: "left",
                    }}
                  >
                    <StatusTag
                      status={task.taskStatus}
                      prUrl={
                        task.prNumber
                          ? `https://github.com/${task.owner.name}/${task.repoName}/pull/${task.prNumber}`
                          : undefined
                      }
                      size="md"
                    />
                  </Td>
                  <Td
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                      paddingRight: "15px",
                      textAlign: "right",
                    }}
                  >
                    <RadialButton
                      onClick={() => openTask(task)}
                      isDisabled={openingTaskId !== null}
                      isLoading={
                        openingTaskId !== null && openingTaskId === task.taskId
                      }
                      size="sm"
                      boxShadow="none"
                      rightIcon={ChevronRightIcon}
                    >
                      Open
                    </RadialButton>
                  </Td>
                </motion.tr>
              ))}
            </Tbody>
          </Table>
        </Box>

        <Box display={{ base: "block", md: "none" }} w="full">
          <HStack
            justify="space-between"
            p={4}
            borderBottom="1px solid rgba(255, 255, 255, 0.2)"
          >
            <Text
              fontSize="12px"
              textTransform="uppercase"
              letterSpacing="0.05em"
            >
              Repository
            </Text>
            <AddDirectory shouldPulse={tasks.length === 0} />
          </HStack>

          {fetchingTasks &&
            Array.from({ length: lastAmountTasks }).map((_, i) => (
              <Box
                key={i}
                p={4}
                borderBottom="1px solid rgba(255, 255, 255, 0.1)"
              >
                <Skeleton h="50px" />
              </Box>
            ))}

          {tasks.map((task: TaskStatus, index: number) => (
            <motion.div
              key={`mobile-${task.taskId}`}
              data-repo-id={task.taskId}
              initial={{ opacity: 0 }}
              animate={{
                opacity: 1,
                transition: {
                  delay: 0.05 * index,
                },
              }}
              whileHover={{
                backgroundColor: "rgba(25, 100, 255, 0.075)",
                transition: {
                  duration: 0.1,
                },
              }}
              onContextMenu={(e) => handleContextMenu(e, task)}
            >
              <HStack
                justify="space-between"
                align="flex-start"
                w="full"
                p={4}
                borderBottom="1px solid rgba(255, 255, 255, 0.1)"
                display="flex"
                alignItems="center"
              >
                <HStack spacing={3} align="flex-start">
                  <Tooltip label={task.owner.name}>
                    <Avatar
                      size="xs"
                      src={task.owner.avatarUrl}
                      name={task.owner.name}
                    />
                  </Tooltip>
                  <VStack align="start" spacing={1}>
                    <Text fontWeight="medium">{task.title}</Text>
                    <VStack
                      align="start"
                      spacing={0}
                      fontSize="sm"
                      color="gray.500"
                    >
                      <HStack spacing={1} alignItems="center">
                        <RiFolderLine size={12} />
                        <Text as="span">{task.workspaceName}</Text>
                      </HStack>
                      <HStack spacing={1} alignItems="center">
                        <RiGithubFill size={12} />
                        <Text as="span">{task.repoName}</Text>
                        {task.issueNumber && (
                          <Button
                            as="a"
                            href={`https://github.com/${task.owner.name}/${task.repoName}/issues/${task.issueNumber}`}
                            target="_blank"
                            size="xs"
                            variant="ghost"
                            colorScheme={
                              task.issueClosed === true ? "purple" : "blue"
                            }
                            rightIcon={<ExternalLinkIcon boxSize={3} />}
                            height="18px"
                            minW="auto"
                            mt={0.5}
                            px={1}
                            onClick={(e) => e.stopPropagation()}
                            fontWeight="normal"
                          >
                            Issue #{task.issueNumber}
                          </Button>
                        )}
                      </HStack>
                    </VStack>
                  </VStack>
                </HStack>
                <RadialButton
                  onClick={() => openTask(task)}
                  isDisabled={openingTaskId !== null}
                  isLoading={
                    openingTaskId !== null && openingTaskId === task.taskId
                  }
                  size="sm"
                  boxShadow="none"
                  rightIcon={ChevronRightIcon}
                >
                  Open
                </RadialButton>
              </HStack>
            </motion.div>
          ))}
        </Box>

        <Menu
          isOpen={menuOpen}
          onClose={() => {
            setMenuOpen(false);
          }}
          placement="auto"
        >
          <RightClickMenu
            isOpen={menuOpen}
            position={menuPosition}
            onOpen={() => {
              openTask(rightClickedTask);
            }}
            onDelete={() => {
              deleteTaskOp(rightClickedTask);
            }}
          />
        </Menu>
      </TableContainer>
    </>
  );
}
