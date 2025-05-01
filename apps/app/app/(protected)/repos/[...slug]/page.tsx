"use client";

import { RadialButton } from "@/app/components/radial-button";
import { Recording, toSnakeCase } from "@/app/types/recording";
import { TaskState } from "@/app/types/task";
import { closeTask } from "@/app/utils/functions/task";
import { useTaskStore } from "@/app/utils/stores/task";
import { ChevronLeftIcon } from "@chakra-ui/icons";
import { Box, Text, useToast } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { useAuth } from "@utils/auth";
import { connectSocket, setupSocketCallbacks, useSocket } from "@utils/socket";
import { useWebviewStore } from "@utils/stores/website-preview";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import SidebarLayout from "./components/body/sidebar";
import LoadingModal from "./components/loading-modal";
import PreviewBox from "./components/preview/preview-panel";

const LeaveOverlay = () => {
  const router = useRouter();
  const { task } = useTaskStore();
  const { emit } = useSocket();

  const goBack = async () => {
    router.push("/home");
    emit("soft_close_task", {
      task_id: task.taskId,
    });
    await closeTask();
  };

  const slideUpAnimation = keyframes`
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
`;

  return (
    <Box
      h="400px"
      w="calc(100vw - 61px)"
      position="fixed"
      bottom="0"
      left="61px"
      background="linear-gradient(to bottom, rgba(0,10,30,0) 0%, rgba(5,15,30,0.5) 30%, rgba(5,15,30,1) 95%)"
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      gap={4}
      pt="200px"
      animation={`${slideUpAnimation} 0.6s ease-out`}
      sx={{
        backfaceVisibility: "hidden",
        willChange: "transform, opacity",
      }}
      zIndex={15}
    >
      <Text color="white" fontSize="lg" fontWeight="medium">
        Speck is fixing the bug. You can leave now.
      </Text>
      <RadialButton
        onClick={goBack}
        size="md"
        bg={["rgba(255, 50, 50, 1)", "rgba(200, 30, 30, 1)"]}
        hoveredBg={["rgba(255, 100, 100, 0.3)", "rgba(200, 30, 30, 0.3)"]}
        border="1px solid rgba(225, 80, 80, 1)"
        boxShadow="0px 0px 40px 0px rgba(200, 30, 30, 1)"
        leftIcon={ChevronLeftIcon}
      >
        Go Back
      </RadialButton>
    </Box>
  );
};

export default function TaskPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const resolvedParams = use(params);
  const { token } = useAuth();
  const { task, updateUIState, updateTask } = useTaskStore();
  const { setUrl } = useWebviewStore();
  const toast = useToast();
  const [isInitialized, setIsInitialized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const { sandboxBaseUrl } = useWebviewStore();
  const { emit } = useSocket();

  useEffect(() => {
    const checkMobile = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobileDevice =
        /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(
          userAgent,
        );
      setIsMobile(isMobileDevice);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);

    if (!isInitialized) {
      setIsInitialized(true);
    }

    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    if (!isInitialized && token) {
      setupSocketCallbacks(toast);
      setIsInitialized(true);
    }
  }, [token, isInitialized]);

  useEffect(() => {
    if (token && resolvedParams.slug) {
      if (resolvedParams.slug.length === 1) {
        if (
          !/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(
            resolvedParams.slug[0],
          )
        ) {
          console.warn("Invalid slug");
          return;
        }

        const newSocket = connectSocket(
          token,
          resolvedParams.slug[0],
          toast,
          false,
        );
        if (newSocket) {
          console.log("Socket connected");
          setupSocketCallbacks(toast);
        } else {
          console.warn("Failed to connect to socket");
        }
      } else if (
        resolvedParams.slug.length === 2 &&
        resolvedParams.slug[0] === "preview"
      ) {
        console.log("Preview mode");
        const newSocket = connectSocket(
          token,
          resolvedParams.slug[0],
          toast,
          true,
        );
        if (newSocket) {
          console.log("Socket connected");
          setupSocketCallbacks(toast);
        } else {
          console.warn("Failed to connect to socket");
        }
        return;
      } else {
        console.warn("Invalid slug");
      }
    }
  }, [token, resolvedParams.slug, toast]);

  useEffect(() => {
    if (task.currentWorkspace?.workspaceName) {
      document.title = `Speck | ${task.currentWorkspace.workspaceName}`;
    }
  }, [task.currentWorkspace?.workspaceName]);

  useEffect(() => {
    if (!task.currentWorkspace?.settings?.rootDirectory || !sandboxBaseUrl) {
      return;
    }
    const handleMessage = (event: MessageEvent) => {
      const { type } = event.data;
      if (type === "url") {
        const { url } = event.data;
        const { pathname } = new URL(url);
        const parts = pathname.split("/");
        let cleanPath = pathname;
        if (parts.length >= 4 && parts[1] === "preview") {
          cleanPath = "/" + parts.slice(4).join("/");
        }
        setUrl(cleanPath);
      }
      if (type === "save_recording") {
        const { data } = event.data;
        if (!data || !data.events || !data.events.length) {
          console.warn("Invalid recording data received:", data);
          return;
        }
        const newRecording: Recording = {
          id: uuidv4(),
          events: data.events,
          baseUrl: sandboxBaseUrl,
          initialUrl: data.initialUrl,
          duration: data.duration,
          viewportSize: data.viewportSize,
          name: `Recording ${new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}`,
          annotation: data.annotation,
          consoleLogs: data.consoleLogs,
          systemInfo: data.systemInfo,
        };
        emit("submit_recording", {
          task_id: task.taskId,
          git_repo_id: task.currentWorkspace?.gitRepoId,
          workspace_name: task.currentWorkspace?.workspaceName,
          recording_data: toSnakeCase(newRecording),
        });

        updateTask({
          taskState: TaskState.RECORDING_SENT,
        });
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [task.currentWorkspace?.settings?.rootDirectory, sandboxBaseUrl]);

  useEffect(() => {
    if (!isInitialized) {
      updateUIState({ sidebarExpanded: false });
      setIsInitialized(true);
    }
  }, []);

  return (
    <Box w="100vw" h="100vh" position="relative" overflow="hidden">
      <LoadingModal />
      <Box h="full" w="full" position="relative">
        <SidebarLayout
          sidebarExpanded={task.uiState.sidebarExpanded || false}
          setSidebarExpanded={(expanded) =>
            updateUIState({ sidebarExpanded: expanded })
          }
          isDragging={isDragging}
        />
        {!isMobile && (
          <PreviewBox
            isDragging={isDragging}
            setIsDragging={setIsDragging}
            sidebarExpanded={task.uiState.sidebarExpanded || false}
          />
        )}
        {task.taskState >= TaskState.ISSUE_CREATION_STARTED &&
          task.taskState < TaskState.PR_CREATED && <LeaveOverlay />}
      </Box>
    </Box>
  );
}
