"use client";

import { RadialButton } from "@/app/components/radial-button";
import { useTaskStore } from "@/app/utils/stores/task";
import {
  Box,
  FormControl,
  FormLabel,
  Input,
  Spinner,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";

interface PullRequestProps {
  token: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function PullRequest({
  token,
  isOpen,
  onClose,
}: PullRequestProps) {
  const { task } = useTaskStore();
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [isPrCreating, setIsPrCreating] = useState(false);
  const [hasEdits, setHasEdits] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [commitDescription, setCommitDescription] = useState("");
  const [branchName, setBranchName] = useState("");

  const getPrInfo = async () => {
    setIsDataLoading(true);
    setCommitMessage("");
    setCommitDescription("");
    setBranchName("");
    setHasEdits(false);
    setIsPrCreating(false);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/repos/persistence/pull_request/get_info/${task.taskId}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      if (data.success) {
        const { commit_message, commit_description, branch_name } = data;
        setHasEdits(
          Boolean(commit_message || commit_description || branch_name),
        );
        setCommitMessage(commit_message || "");
        setCommitDescription(commit_description || "");
        setBranchName(branch_name || "");
      } else {
        setHasEdits(false);
      }
    } catch (error) {
      console.error("Error getting PR info:", error);
    } finally {
      setIsDataLoading(false);
    }
  };

  const createPullRequest = async () => {
    setIsPrCreating(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/repos/persistence/pull_request/create`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            commit_message: commitMessage,
            commit_description: commitDescription,
            branch_name: branchName,
            task_id: task.taskId,
          }),
        },
      );

      if (!res.ok) {
        const errorData = await res.json();
        console.error("Error response:", errorData);
        throw new Error(
          `HTTP error! status: ${res.status}, message: ${JSON.stringify(errorData)}`,
        );
      }

      const data = await res.json();
      const { success, url } = data;
      if (success) {
        window.open(url, "_blank");
        onClose();
      } else {
        throw new Error("Failed to create pull request");
      }
    } catch (error) {
      console.error("Error creating pull request:", error);
    } finally {
      setIsPrCreating(false);
    }
  };

  useEffect(() => {
    if (isOpen && !isDataLoading) {
      getPrInfo();
    }
  }, [isOpen]);

  return (
    <>
      {isDataLoading ? (
        <Box
          w="full"
          h="200px"
          display="flex"
          justifyContent="center"
          alignItems="center"
        >
          <Spinner />
        </Box>
      ) : !hasEdits ? (
        <Text w="full" textAlign="center" p={4}>
          No edits. Make some changes to create a pull request.
        </Text>
      ) : (
        <VStack spacing={4} align="stretch">
          <FormControl>
            <FormLabel>Commit Message</FormLabel>
            <Input
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              size="sm"
              borderRadius="md"
            />
          </FormControl>
          <FormControl>
            <FormLabel>Commit Description</FormLabel>
            <Textarea
              value={commitDescription}
              onChange={(e) => setCommitDescription(e.target.value)}
              size="sm"
              borderRadius="md"
            />
          </FormControl>
          <FormControl mb={4}>
            <FormLabel>Branch Name</FormLabel>
            <Input
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              size="sm"
              borderRadius="md"
            />
          </FormControl>
          <RadialButton
            w="full"
            onClick={createPullRequest}
            isLoading={isPrCreating}
            isDisabled={!hasEdits}
            shouldPulse
          >
            Create Pull Request
          </RadialButton>
        </VStack>
      )}
    </>
  );
}
