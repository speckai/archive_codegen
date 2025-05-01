"use client";

import { Modal, ModalOverlay } from "@/app/components/modal";
import { useEffect, useState } from "react";
import AddRepo from "./add-repo";
import Main from "./main";

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

interface CreateTaskModalProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  issueDetails?: IssueDetails | null;
}

export default function CreateTaskModal({
  isOpen,
  setIsOpen,
  issueDetails = null,
}: CreateTaskModalProps) {
  const [mode, setMode] = useState<"task" | "addRepo">("task");

  useEffect(() => {
    setMode("task");
  }, [isOpen]);

  return (
    <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} size="5xl">
      <ModalOverlay />
      {mode === "task" && (
        <Main
          setIsOpen={setIsOpen}
          setMode={setMode}
          issueDetails={issueDetails}
        />
      )}
      {mode === "addRepo" && <AddRepo isOpen={isOpen} setMode={setMode} />}
    </Modal>
  );
}
