import UserSettingsModalComponent from "./modal";

interface UserSettingsModalProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export function UserSettingsModal({
  isOpen,
  setIsOpen,
}: UserSettingsModalProps) {
  return <UserSettingsModalComponent isOpen={isOpen} setIsOpen={setIsOpen} />;
}
