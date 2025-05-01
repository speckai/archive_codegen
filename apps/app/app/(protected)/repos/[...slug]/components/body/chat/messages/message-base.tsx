import {
  Avatar,
  Box,
  CircularProgress,
  HStack,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { ChatMessage } from "@ctypes/chat-message";
import { useAuth } from "@utils/auth";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";

interface MessageItemProps {
  message: ChatMessage;
  children: React.ReactNode;
  isLast?: boolean;
}
export default function MessageItem({
  message,
  children,
  isLast,
}: MessageItemProps) {
  const { user } = useAuth();
  const [shouldAnimate, setShouldAnimate] = useState<boolean | null>(null);

  useEffect(() => {
    if (isLast) {
      setShouldAnimate(true);
      setTimeout(() => {
        setShouldAnimate(false);
      }, 1000);
    }
  }, [message]);

  const shouldWeAnimate = () => {
    if (shouldAnimate === null && isLast) {
      return true;
    }
    return shouldAnimate;
  };

  return (
    <Box
      bg={message.role === "assistant" ? "rgba(0,10,30,0)" : "rgba(0,0,0,0)"}
      color="black"
      p={2}
      px={4}
      w="full"
      alignSelf={message.role === "assistant" ? "start" : "end"}
      borderBottom={isLast ? "0px" : "1px"}
      borderBottomColor="rgba(255,255,255,0.07)"
      pb={6}
    >
      <VStack align={message.role === "assistant" ? "start" : "end"} w="full">
        <HStack
          spacing={2}
          alignItems="center"
          flexDirection={message.role === "user" ? "row-reverse" : "row"}
          w="full"
        >
          <motion.div
            initial={{ opacity: shouldWeAnimate() === false ? 0 : 1 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Avatar
              size="xs"
              src={
                message.role === "assistant"
                  ? "/logos/no-bg/speck-logo-1024.webp"
                  : user?.user_metadata.avatar_url
              }
              name={
                message.role === "assistant"
                  ? "Speck"
                  : user?.user_metadata.name
              }
            />
          </motion.div>
          <motion.div
            initial={{
              opacity: shouldWeAnimate() ? 0 : 1,
              x: shouldWeAnimate() ? (message.role === "user" ? 20 : -20) : 0,
            }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Text
              fontSize="xs"
              fontWeight="bold"
              textTransform="uppercase"
              color="white"
            >
              {message.role === "assistant" ? "Speck" : "You"}
            </Text>
          </motion.div>
          {message.role === "assistant" && !message.messageData && (
            <motion.div
              initial={{ opacity: shouldWeAnimate() ? 0 : 1 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <CircularProgress isIndeterminate size={4} mb={1} />
            </motion.div>
          )}
        </HStack>
        {message.role === "assistant" ? (
          <>
            {!message.messageData ? (
              <>
                <Skeleton height="15px" width="80%" />
                <Skeleton height="15px" width="60%" />
              </>
            ) : (
              <motion.div
                initial={{ opacity: shouldWeAnimate() ? 0 : 1 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
              >
                {children}
              </motion.div>
            )}
          </>
        ) : (
          <motion.div
            initial={{ opacity: shouldWeAnimate() ? 0 : 1 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            style={{ width: "100%" }}
          >
            {children}
          </motion.div>
        )}
      </VStack>
    </Box>
  );
}
