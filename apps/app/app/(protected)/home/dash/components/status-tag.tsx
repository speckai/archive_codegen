"use client";

import { ExternalLinkIcon, WarningIcon } from "@chakra-ui/icons";
import { HStack, Icon, Spinner, Tag, TagLabel } from "@chakra-ui/react";

interface StatusTagProps {
  status: string;
  prUrl?: string;
  size?: "sm" | "md";
}

export default function StatusTag({
  status,
  prUrl,
  size = "md",
}: StatusTagProps) {
  const getTagProps = (status: string) => {
    switch (status) {
      case "active":
        return {
          colorScheme: "blue",
          label: "Active",
          showSpinner: true,
        };
      case "completed":
        return {
          colorScheme: "green",
          label: "Completed",
        };
      case "pr_open":
        return {
          colorScheme: "blue",
          label: "PR Open",
        };
      case "pr_merged":
        return {
          colorScheme: "green",
          label: "PR Merged",
        };
      case "pr_closed":
        return {
          colorScheme: "red",
          label: "PR Closed",
        };
      case "blocked":
        return {
          colorScheme: "red",
          label: "Blocked",
        };
      case "cancelled":
        return {
          colorScheme: "red",
          label: "Cancelled",
        };
      default:
        return {
          colorScheme: "gray",
          label: "Ready",
        };
    }
  };

  const { colorScheme, label, showSpinner } = getTagProps(status);

  const onClick = () => {
    if (prUrl) {
      window.open(prUrl, "_blank");
    }
  };

  return (
    <Tag
      size={size}
      colorScheme={colorScheme}
      variant="subtle"
      onClick={onClick}
      cursor={prUrl ? "pointer" : "default"}
    >
      <HStack spacing={2}>
        {status === "blocked" && <WarningIcon color="red.500" />}
        {showSpinner && <Spinner size="xs" />}
        <TagLabel>{label}</TagLabel>
        {prUrl && <Icon as={ExternalLinkIcon} boxSize={4} color="blue.500" />}
      </HStack>
    </Tag>
  );
}
