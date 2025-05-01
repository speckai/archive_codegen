"use client";

import { useAuth } from "@/app/utils/auth";
import { useRecorderStore } from "@/app/utils/stores/recorder";
import { useTaskStore } from "@/app/utils/stores/task";
import { Box, Spinner, Text, VStack } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { useWebviewStore } from "@utils/stores/website-preview";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import PreviewNavbar from "./components/preview-navbar";
import PreviewWindow from "./components/preview-window";

interface PreviewBoxProps {
  isDragging: boolean;
  setIsDragging: (isDragging: boolean) => void;
  sidebarExpanded: boolean;
}

export default function PreviewBox({
  isDragging,
  setIsDragging,
  sidebarExpanded,
}: PreviewBoxProps) {
  const {
    iframeLastUpdated,
    url,
    sandboxBaseUrl,
    isLoading,
    setIsLoading,
    previewWidth,
    setWebviewSettings,
    getFullUrl,
  } = useWebviewStore();

  const { isRecording, isReplaying } = useRecorderStore();

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [fullUrlState, setFullUrlState] = useState(getFullUrl());
  const { token } = useAuth();
  const { task } = useTaskStore();
  const [hasError, setHasError] = useState(false);
  const [currentIframeUrl, setCurrentIframeUrl] = useState("");

  const [isHandleHovered, setIsHandleHovered] = useState(false);

  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const isDraggingRef = useRef(isDragging);
  useEffect(() => {
    isDraggingRef.current = isDragging;
  }, [isDragging]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (
        event.data?.type === "SANDBOX_READY" &&
        iframeRef.current?.contentWindow
      ) {
        iframeRef.current.contentWindow.postMessage(
          {
            type: "INJECT_SCRIPT",
            src: `${process.env.NEXT_PUBLIC_API_URL}/client_scripts/recorder.js`,
          },
          "*",
        );
        iframeRef.current.contentWindow.postMessage(
          {
            type: "INJECT_SCRIPT",
            src: `${process.env.NEXT_PUBLIC_API_URL}/client_scripts/devtools.js`,
          },
          "*",
        );
      } else if (event.data?.type === "redirecter_ready") {
        console.log("Redirecter ready");
        iframeRef.current?.contentWindow?.postMessage(
          {
            type: "set_base_url",
            data: { baseUrl: sandboxBaseUrl },
          },
          "*",
        );
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [iframeRef.current]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const checkWebsiteExists = () => {
      if (iframeRef.current && iframeRef.current.src !== fullUrlState) {
        setIsLoading(true);
      }
    };

    if (isLoading) {
      intervalId = setInterval(checkWebsiteExists, 1000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isLoading, fullUrlState]);

  useEffect(() => {
    if (url.includes("http://") || url.includes("https://")) {
      setFullUrlState(url);
      return;
    }

    let trimmedBaseUrl = sandboxBaseUrl.endsWith("/")
      ? sandboxBaseUrl.slice(0, -1)
      : sandboxBaseUrl;

    setFullUrlState(`${trimmedBaseUrl}${url}`);
  }, [sandboxBaseUrl, url]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const checkForBackendError = () => {
      if (!fullUrlState || !iframeRef.current) {
        return;
      }

      try {
        if (iframeRef.current.contentWindow?.location.href) {
          const iframeWindow = iframeRef.current.contentWindow;

          if (iframeWindow && iframeWindow.document) {
            const content = iframeWindow.document.body?.textContent;
            if (content?.includes("Error connecting to backend")) {
              console.log("Backend connection error detected, refreshing...");
              iframeRef.current.src = fullUrlState;
            }
          }
        }
      } catch (error) {
        console.debug(
          "Could not access iframe content (likely cross-origin):",
          error,
        );
      }
    };

    intervalId = setInterval(checkForBackendError, 1000);
    return () => clearInterval(intervalId);
  }, [fullUrlState]);

  // Transform localhost URLs to use baseUrl
  const transformLocalhostUrl = (url: string) => {
    try {
      const urlObj = new URL(url);
      if (urlObj.hostname === "localhost") {
        const path = urlObj.pathname;
        const queryString = urlObj.search;
        const trimmedBaseUrl = sandboxBaseUrl.endsWith("/")
          ? sandboxBaseUrl.slice(0, -1)
          : sandboxBaseUrl;
        return `${trimmedBaseUrl}${path}${queryString}`;
      }
    } catch (error) {
      console.error("Error transforming URL:", error);
    }
    return url;
  };

  // Monitor iframe URL changes
  useEffect(() => {
    if (!iframeRef.current) return;

    const checkIframeUrl = () => {
      try {
        const iframe = iframeRef.current;
        if (iframe && iframe.contentWindow) {
          const currentUrl = iframe.contentWindow.location.href;
          if (currentUrl && currentUrl !== currentIframeUrl) {
            // Transform URL if it's a localhost URL
            const transformedUrl = transformLocalhostUrl(currentUrl);
            setCurrentIframeUrl(transformedUrl);
            console.log("Iframe URL changed:", transformedUrl);

            // If URL was transformed, update the iframe src
            if (transformedUrl !== currentUrl) {
              iframe.src = transformedUrl;
            }
          }
        }
      } catch (error) {
        // Silently handle cross-origin errors
      }
    };

    const intervalId = setInterval(checkIframeUrl, 500);
    return () => clearInterval(intervalId);
  }, [iframeRef.current, currentIframeUrl, sandboxBaseUrl]);

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDraggingRef.current) {
      return;
    }

    const delta = e.clientX - startXRef.current;
    let newWidth = startWidthRef.current - (delta / window.innerWidth) * 100;

    setWebviewSettings({ previewWidth: newWidth });
  };

  const handleMouseUp = () => {
    if (!sidebarExpanded) {
      return;
    }

    setIsDragging(false);
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!sidebarExpanded) {
      return;
    }

    e.preventDefault();
    startXRef.current = e.clientX;
    startWidthRef.current = previewWidth;

    setIsDragging(true);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  useEffect(() => {
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const recordingPulseBorder = keyframes`
    0% { border-color: rgba(255, 0, 0, 0.8); }
    50% { border-color: rgba(255, 0, 0, 0.3); }
    100% { border-color: rgba(255, 0, 0, 0.8); }
  `;

  const replayingPulseBorder = keyframes`
    0% { border-color: rgba(63, 131, 248, 0.8); }
    50% { border-color: rgba(63, 131, 248, 0.3); }
    100% { border-color: rgba(63, 131, 248, 0.8); }
  `;

  return (
    <>
      <motion.div
        animate={{
          width: `calc(${previewWidth}vw - 60px)`,
        }}
        transition={{ duration: isDragging ? 0 : 0.2, ease: "easeOut" }}
        style={{
          height: "calc(100%)",
          position: "absolute",
          right: 0,
          top: 0,
          overflow: "hidden",
          display: previewWidth > 0 ? "block" : "none",
        }}
      >
        {previewWidth > 0 && (
          <>
            <AnimatePresence>
              {isLoading && (
                <motion.div
                  initial={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5 }}
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                  }}
                >
                  <VStack spacing={6}>
                    <Spinner color="white" size="lg" />
                    <Text color="gray.200" textAlign="center">
                      Starting Webview...
                    </Text>
                  </VStack>
                </motion.div>
              )}
            </AnimatePresence>

            {hasError && (
              <Box
                position="absolute"
                top="50%"
                left="50%"
                transform="translate(-50%, -50%)"
                textAlign="center"
              >
                <Text color="white">Failed to load preview</Text>
                <Text color="white" fontSize="sm">
                  Please check if the server is running
                </Text>
              </Box>
            )}

            <Box
              pt="5px"
              w="100%"
              h="100%"
              paddingBottom="10px"
              paddingX="10px"
              display="flex"
              flexDirection="column"
              justifyContent="center"
              alignItems="center"
              borderLeft="1px solid rgba(255, 255, 255, 0.25)"
              backgroundColor="#0C121D"
            >
              <Box
                overflow="hidden"
                w="100%"
                h="100%"
                display="flex"
                flexDirection="column"
                alignItems="center"
              >
                <PreviewNavbar />
                <Box
                  borderRadius="xl"
                  overflow="hidden"
                  w="100%"
                  h="calc(100% - 40px)"
                  border={
                    isRecording || isReplaying
                      ? "1px solid"
                      : "1px solid rgba(255, 255, 255, 0.1)"
                  }
                  animation={
                    isRecording
                      ? `${recordingPulseBorder} 1.5s infinite`
                      : isReplaying
                        ? `${replayingPulseBorder} 1.5s infinite`
                        : undefined
                  }
                  position="relative"
                >
                  {fullUrlState !== "/" && (
                    <iframe
                      id="speck-preview-iframe"
                      ref={iframeRef}
                      key={fullUrlState + iframeLastUpdated}
                      src={fullUrlState}
                      sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-storage-access-by-user-activation allow-modals allow-downloads allow-pointer-lock"
                      style={{
                        width: "100%",
                        height: "100%",
                        display: isLoading ? "none" : "block",
                        pointerEvents: isDragging ? "none" : "auto",
                      }}
                      onLoad={() => {
                        iframeRef.current?.contentWindow?.postMessage(
                          {
                            type: "endpoint",
                            data: {
                              token: token,
                              taskId: task.taskId,
                              endpoint: `${process.env.NEXT_PUBLIC_API_URL}/repos/website-data`,
                            },
                          },
                          "*",
                        );
                        setIsLoading(false);
                      }}
                      onError={() => {
                        console.error(
                          "Failed to load iframe with URL:",
                          fullUrlState,
                        );
                        setHasError(true);
                      }}
                    />
                  )}
                  <PreviewWindow />
                </Box>
              </Box>
            </Box>

            <Box
              position="absolute"
              top={0}
              left={0}
              height="100%"
              width="15px"
              cursor={sidebarExpanded ? "ew-resize" : "auto"}
              zIndex={1010}
              onMouseEnter={() => {
                if (!sidebarExpanded) {
                  return;
                }
                setIsHandleHovered(true);
              }}
              onMouseLeave={() => {
                if (!sidebarExpanded) {
                  return;
                }
                setIsHandleHovered(false);
              }}
              onMouseDown={handleMouseDown}
              style={{ backgroundColor: "transparent" }}
            >
              <Box
                position="absolute"
                top={0}
                left={0}
                height="100%"
                style={{
                  width: isHandleHovered || isDragging ? "8px" : "0px",
                  transition: "width 0.2s",
                  backgroundColor: "rgba(255, 255, 255, 0.3)",
                  overflow: "hidden",
                }}
              >
                <Box
                  position="absolute"
                  top="50%"
                  left="50%"
                  transform="translate(-50%, -50%)"
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                  justifyContent="center"
                  gap="5px"
                >
                  <Box
                    width="4px"
                    height="4px"
                    borderRadius="50%"
                    bg="white"
                    opacity={0.4}
                  />
                  <Box
                    width="4px"
                    height="4px"
                    borderRadius="50%"
                    bg="white"
                    opacity={0.4}
                  />
                  <Box
                    width="4px"
                    height="4px"
                    borderRadius="50%"
                    bg="white"
                    opacity={0.4}
                  />
                </Box>
              </Box>
            </Box>
          </>
        )}
      </motion.div>
    </>
  );
}
