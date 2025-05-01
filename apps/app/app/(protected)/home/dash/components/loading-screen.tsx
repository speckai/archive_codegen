import { Box, HStack, Image, Text, VStack } from "@chakra-ui/react";
import { useAuth } from "@utils/auth";
import { AnimatePresence, motion } from "framer-motion";

export enum UpdateState {
  Authenticating,
  Checking,
  Updating,
  None,
}

const WelcomeMessage = ({ userName }: { userName: string }) => (
  <HStack spacing={1}>
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.4, type: "easeInOut", delay: 0.5 }}
    >
      <Text textColor="gray.300" fontSize="xl">
        Welcome back
        {userName ? ", " : ""}
      </Text>
    </motion.div>
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.4, type: "easeInOut", delay: 1 }}
    >
      <Text fontWeight="bold" textColor="gray.200" fontSize="xl">
        {userName}
      </Text>
    </motion.div>
  </HStack>
);

export default function LoadingScreen() {
  const { user } = useAuth();

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.5 }}
        style={{
          overflow: "hidden",
        }}
      >
        <Box
          w="100vw"
          h="100vh"
          display="flex"
          justifyContent="center"
          alignItems="center"
          position="absolute"
          bgGradient="radial(rgba(10,20,50,1), rgba(2,5,10,1))"
          zIndex="1000"
          overflow="hidden"
        >
          <VStack spacing={4}>
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2, type: "easeInOut", delay: 0.2 }}
            >
              <Image
                src="/logos/no-bg/speck-logo-512.webp"
                alt="logo"
                w="75px"
              />
            </motion.div>
            <WelcomeMessage
              userName={user?.user_metadata.name?.split(" ")[0]}
            />
          </VStack>
        </Box>
      </motion.div>
    </AnimatePresence>
  );
}
