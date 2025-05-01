import { Button, Icon, Text, useDisclosure } from "@chakra-ui/react";
import { useSocket } from "@utils/socket";
import { IoIosInformationCircleOutline } from "react-icons/io";
import DevPanelModal from "./modal";

export default function DevPanelButton() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isConnected } = useSocket();

  return (
    <Button
      size="xs"
      variant="ghost"
      onClick={onOpen}
      justifyContent="space-between"
      width="34px"
      alignItems="center"
      px={0.5}
      mr={1}
      cursor="pointer"
      pointerEvents="auto"
      userSelect="auto"
    >
      <DevPanelModal isOpen={isOpen} onClose={onClose} />

      <Text fontSize="md" color={isConnected ? "green.500" : "red.500"}>
        ●
      </Text>
      <Icon
        as={IoIosInformationCircleOutline}
        color={isConnected ? "white" : "yellow.500"}
        fontSize="md"
      />
    </Button>
  );
}
