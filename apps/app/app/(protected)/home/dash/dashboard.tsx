import { useToast } from "@chakra-ui/react";
import {
  MotionBox,
  MotionHStack,
  MotionImage,
  MotionText,
  MotionVStack,
} from "@components/animated";
import { useAuth } from "@utils/auth";
import { getAddedRepos } from "@utils/functions/repos";
import { closeTask } from "@utils/functions/task";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import CreateTaskModal from "./components/create-task/modal";
import LoadingScreen from "./components/loading-screen";
import TaskTable from "./components/task-table";
import UserButton from "./components/user-button";

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

function DashboardContent() {
  const [hasLoaded, setHasLoaded] = useState<boolean | null>(null);
  const { user, token } = useAuth();
  const searchParams = useSearchParams();
  const toast = useToast();
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [repositories, setRepositories] = useState<any[]>([]);
  const [issueDetails, setIssueDetails] = useState<IssueDetails | null>(null);

  useEffect(() => {
    if (sessionStorage.getItem("loaded") === "true") {
      setHasLoaded(true);
    } else {
      setHasLoaded(false);
    }
    closeTask();
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }
    setTimeout(() => {
      sessionStorage.setItem("loaded", "true");
      setHasLoaded(true);
    }, 2000);
  }, [token]);

  useEffect(() => {
    const fetchRepos = async () => {
      if (!token) {
        return;
      }
      try {
        const result = await getAddedRepos(token);
        setRepositories(result.addedRepos || []);
      } catch (error) {
        console.error("Error fetching repositories:", error);
      }
    };

    fetchRepos();
  }, [token]);

  useEffect(() => {
    if (!token || repositories.length === 0 || !hasLoaded) {
      return;
    }

    const repoId = searchParams.get("repo_id");
    const issueNumber = searchParams.get("issue_number");

    if (repoId) {
      const repoExists = repositories.some(
        (repo) => repo.gitRepoId.toString() === repoId,
      );

      if (repoExists) {
        const selectedRepo = repositories.find(
          (repo) => repo.gitRepoId.toString() === repoId,
        );
        if (selectedRepo) {
          setIsCreateTaskOpen(true);

          if (issueNumber) {
            fetchIssueDetails(issueNumber, repoId);
          }
        }
      } else {
        toast({
          title: "Repository not found",
          description: "You need to add this repository to your account first.",
          status: "warning",
          duration: 5000,
          isClosable: true,
        });
      }
    } else if (issueNumber) {
      toast({
        title: "Repository ID required",
        description: "A repository ID is required to fetch issue details",
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
    }
  }, [searchParams, repositories, token, toast, hasLoaded]);

  const fetchIssueDetails = async (issueNumber: string, repoId: string) => {
    if (!token || !repoId) {
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/github/issue/details/${repoId}/${issueNumber}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch issue details");
      }

      const data = await response.json();
      if (data.success) {
        setIssueDetails(data.issue);
      }
    } catch (error) {
      console.error("Error fetching issue details:", error);
      toast({
        title: "Error",
        description: "Failed to fetch issue details",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  if (!hasLoaded) {
    return <LoadingScreen />;
  }

  return (
    <>
      <MotionVStack
        w="full"
        h="full"
        pt="20px"
        display="flex"
        justifyContent="center"
        px={4}
        pb={4}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <MotionHStack
          justifyContent="space-between"
          width="100%"
          px={4}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0 }}
        >
          <MotionHStack spacing={4}>
            <MotionImage
              src="/logos/no-bg/speck-logo-512.webp"
              alt="logo"
              width={30}
              height={30}
              initial={{ x: -10 }}
              animate={{ x: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              filter="drop-shadow(0 0 10px rgba(30, 80, 200, 1))"
            />
            <MotionText
              fontSize="lg"
              fontWeight="bold"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              Dashboard
            </MotionText>
          </MotionHStack>
          <UserButton user={user} />
        </MotionHStack>

        <MotionBox
          h="95%"
          w="full"
          mt={4}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
        >
          <TaskTable />
        </MotionBox>
      </MotionVStack>

      <CreateTaskModal
        isOpen={isCreateTaskOpen}
        setIsOpen={setIsCreateTaskOpen}
        issueDetails={issueDetails}
      />
    </>
  );
}

export default function Dashboard() {
  return (
    <Suspense>
      <DashboardContent />
    </Suspense>
  );
}
