import { Text, useToast } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@utils/auth";
import { useSocket } from "@utils/socket";
import { useEffect, useState } from "react";

interface DevPanelModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DevPanelModal({ isOpen, onClose }: DevPanelModalProps) {
  const [version, setVersion] = useState<string | null>(null);
  const { isConnected } = useSocket();
  const toast = useToast();
  const { token } = useAuth();

  useEffect(() => {
    const fetchVersion = async () => {
      // const version = await getVersion();
      // setVersion(version);
    };
    fetchVersion();
  }, []);

  const { refetch: sendLogs, isLoading } = useQuery({
    queryKey: ["sendLogs"],
    queryFn: async () => {
      // const logs = await invoke("read_log_file");
      // const response = await fetch(`${baseUrl}/analytics/logs/put`, {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //     Authorization: `Bearer ${token}`,
      //   },
      //   body: JSON.stringify({ error_log: logs }),
      // });
      // return response.json();
    },
    enabled: false,
  });

  const handleSendLogs = async () => {
    // try {
    //   const result = await sendLogs();
    //   if (result.data && result.data.success) {
    //     toast({
    //       title: "Logs sent successfully",
    //       status: "success",
    //       isClosable: false,
    //     });
    //   } else {
    //     throw new Error(`Server responded with status ${result.status}`);
    //   }
    // } catch (error) {
    //   toast({
    //     title: "Failed to send logs",
    //     description: "Please contact Speck support",
    //     status: "error",
    //     isClosable: false,
    //   });
    // }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>App Information</ModalHeader>
        <ModalCloseButton />
        <ModalBody mb={2}>
          <Text>Version: v{version}</Text>
          <Text>
            Socket Connection: {isConnected ? "Connected" : "Disconnected"}
          </Text>
          {!isConnected && (
            <Text color="red.500" fontSize="sm" mt={1}>
              The connection to the server is lost. Please right click and
              refresh the app. <br />
              If the issue persists, please reach out to the Speck team!
            </Text>
          )}
          {/* <Button
            size="sm"
            variant="outline"
            colorScheme="red"
            onClick={handleSendLogs}
            isLoading={isLoading}
            mt={4}
          >
            Send Logs to Speck Team
          </Button> */}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
