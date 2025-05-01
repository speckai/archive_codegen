"use client";

import { useTaskStore } from "@/app/utils/stores/task";
import {
  Box,
  HStack,
  Icon,
  IconButton,
  IconButtonProps,
  Link,
  Text,
  Textarea,
  Tooltip,
} from "@chakra-ui/react";
import { useWebviewStore } from "@utils/stores/website-preview";
import React, { useEffect } from "react";
import { PiPlugBold } from "react-icons/pi";

import { getDisplayUrl } from "@/app/utils/functions/url";
import { Image } from "@chakra-ui/react";
import { HiOutlineExternalLink } from "react-icons/hi";
import {
  IoArrowBackOutline,
  IoArrowForwardOutline,
  IoRefreshOutline,
} from "react-icons/io5";

import { BsPersonWorkspace } from "react-icons/bs";
import { FaExternalLinkAlt, FaGithub } from "react-icons/fa";

interface NavButtonProps {
  icon: React.ReactElement;
  onClick: () => void;
  ariaLabel: string;
  isLoading?: boolean;
}

const NavButton: React.FC<NavButtonProps> = ({
  icon,
  onClick,
  ariaLabel,
  isLoading = false,
}) => (
  <IconButton
    icon={icon as IconButtonProps["icon"]}
    isLoading={isLoading}
    variant="ghost"
    colorScheme="white"
    aria-label={ariaLabel}
    onClick={onClick}
    size="sm"
    p={0}
    m={0}
    borderRadius="full"
    _hover={{
      bg: "rgba(255, 255, 255, 0.2)",
    }}
  />
);

interface UrlInputProps {
  url: string;
  onSubmit: (event: React.FormEvent<HTMLTextAreaElement>) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  port: number;
  openSettingsMenu: (open: boolean) => void;
}

const UrlInput: React.FC<UrlInputProps> = ({
  url,
  onSubmit,
  textareaRef,
  port,
  openSettingsMenu,
}) => {
  return (
    <Box
      display="flex"
      alignItems="center"
      flexGrow={1}
      borderRadius="full"
      border="1px"
      borderColor="rgba(255, 255, 255, 0.4)"
      bg="rgba(0, 0, 0, 0.3)"
      ml={1}
      p={1}
      onClick={() => {
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(
          textareaRef.current.value.length,
          textareaRef.current.value.length,
        );
      }}
    >
      <HStack
        color="gray.300"
        fontSize="xs"
        onClick={() => openSettingsMenu(true)}
        borderRadius="full"
        mr={1}
        spacing={1}
        px={1.5}
        py={0.25}
        bg="rgba(255, 255, 255, 0.2)"
        _hover={{
          bg: "rgba(255, 255, 255, 0.3)",
        }}
      >
        <Icon as={PiPlugBold} size="xs" />
        <Text fontSize="xs">{port}</Text>
      </HStack>
      <Textarea
        color="gray.300"
        fontSize="xs"
        resize="none"
        width="100%"
        borderRightRadius="full"
        p={0}
        border="none"
        overflow="hidden"
        overflowY="scroll"
        rows={1}
        placeholder="/"
        onSubmit={onSubmit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            onSubmit(e);
            e.preventDefault();
          }
          if (e.key === "Escape") {
            textareaRef.current?.blur();
          }
        }}
        onChange={(e) => {
          if (e.target.value.length === 0) {
            e.target.value = "/";
          } else if (e.target.value[0] !== "/") {
            e.target.value = "/" + e.target.value.slice(1);
          }
        }}
        autoCorrect="off"
        defaultValue={url}
        ref={textareaRef}
      />
    </Box>
  );
};

const SpaceInfo = () => {
  const { task } = useTaskStore();
  return (
    <HStack px={3}>
      <Icon as={BsPersonWorkspace} color="gray.500" />
      <Text color="gray.500" fontSize="sm">
        {task.currentWorkspace?.workspaceName}
      </Text>
      <Box w="2px" h="2px" bg="gray.500" borderRadius="full" />

      <Tooltip
        label={
          <HStack p={1}>
            <Image
              src={task.currentWorkspace?.owner?.avatarUrl || ""}
              w="20px"
              h="20px"
              borderRadius="full"
            />
            <Text color="rgba(255,255,255,0.7)" size="sm">
              {task.currentWorkspace?.repoFullName}
            </Text>
          </HStack>
        }
        rounded="full"
        bg="rgba(255,255,255,0)"
        border="1px solid rgba(255,255,255,0.2)"
        backdropFilter="blur(2px)"
      >
        <HStack>
          <Icon as={FaGithub} color="gray.500" />
          <Text color="gray.500" fontSize="sm">
            {task.currentWorkspace?.repoName}
          </Text>
        </HStack>
      </Tooltip>
      {task.currentWorkspace?.issueNumber && (
        <Link
          href={`https://github.com/${task.currentWorkspace?.owner?.name}/${task.currentWorkspace?.repoName}/issues/${task.currentWorkspace?.issueNumber}`}
          isExternal
          color="blue.400"
          fontSize="sm"
          display="flex"
          alignItems="center"
          _hover={{ textDecoration: "none", color: "blue.300" }}
          onClick={(e) => e.stopPropagation()}
          mt={0.5}
        >
          <Text mr={1} fontSize="xs">
            (Issue #{task.currentWorkspace?.issueNumber})
          </Text>
          <Icon as={FaExternalLinkAlt} ml={1} boxSize={2.5} />
        </Link>
      )}
    </HStack>
  );
};
export default function PreviewNavbar() {
  const { url } = useWebviewStore();
  const { task, updateUIState } = useTaskStore();
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const {
    getFullUrl,
    setUrl,
    rerenderIframe,
    goBack,
    goForward,
    resetHistory,
  } = useWebviewStore();

  const onSubmit = (e: React.FormEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    setUrl(e.currentTarget.value);
    rerenderIframe();
    e.currentTarget.blur();
  };
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const restartWebsiteEvent = async () => {
    if (task.currentWorkspace?.gitRepoId) {
      setIsRefreshing(true);
      rerenderIframe();
      setTimeout(() => setIsRefreshing(false), 1000);
    }
  };

  const openSettingsMenu = (open: boolean) => {
    updateUIState({
      isWorkspaceSettingsModalOpen: open,
      workspaceSettingsPanelToShow: "settings",
    });
  };

  useEffect(() => {
    resetHistory();
  }, []);

  const openInNewTab = () => {
    let url = getFullUrl();
    window.open(url, "_blank");
  };

  useEffect(() => {
    if (
      url !== textareaRef.current?.value &&
      url !== undefined &&
      url !== null &&
      textareaRef.current
    ) {
      textareaRef.current.value = getDisplayUrl(url);
    }
  }, [url]);

  return (
    <HStack w="100%" p={0.5} pb={2} spacing={0}>
      <SpaceInfo />

      <NavButton
        icon={<IoArrowBackOutline />}
        onClick={goBack}
        ariaLabel="Back"
      />
      <NavButton
        icon={<IoArrowForwardOutline />}
        onClick={goForward}
        ariaLabel="Forward"
      />
      <NavButton
        icon={<IoRefreshOutline />}
        isLoading={isRefreshing}
        onClick={restartWebsiteEvent}
        ariaLabel="Refresh Page"
      />
      <UrlInput
        url={getDisplayUrl(url)}
        onSubmit={onSubmit}
        textareaRef={textareaRef as React.RefObject<HTMLTextAreaElement | null>}
        port={task.currentWorkspace?.settings?.port || 3000}
        openSettingsMenu={openSettingsMenu}
      />
      <Tooltip label="Open in new tab" placement="bottom-end" fontSize="xs">
        <Box ml={0.5}>
          <NavButton
            icon={<HiOutlineExternalLink />}
            onClick={openInNewTab}
            ariaLabel="Open in new tab"
          />
        </Box>
      </Tooltip>
    </HStack>
  );
}
