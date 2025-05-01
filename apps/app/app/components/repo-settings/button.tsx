import { useTaskStore } from "@/app/utils/stores/task";
import { IconButton } from "@chakra-ui/react";
import { IoMdSettings } from "react-icons/io";
import SettingsModalComponent from "./modal";

export default function RepoSettingsButtonAndModal() {
  const { updateUIState } = useTaskStore();

  const handleSettingsClick = () => {
    updateUIState({ isWorkspaceSettingsModalOpen: true });
  };

  return (
    <>
      <IconButton
        icon={<IoMdSettings size={16} />}
        color="gray.400"
        onClick={handleSettingsClick}
        size="sm"
        aria-label="Settings"
        variant="ghost"
      />
      <SettingsModalComponent />
    </>
  );
}
