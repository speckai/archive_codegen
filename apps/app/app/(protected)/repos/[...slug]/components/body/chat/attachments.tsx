import { Box, HStack, Text } from "@chakra-ui/react";
import { motion } from "framer-motion";
import React from "react";

import { Recording } from "@ctypes/recording";
import RecordingItem from "./recordings/item";

interface AttachmentsBoxProps {
  isOpen: boolean;
  recordings: Recording[];
  setRecordings: React.Dispatch<React.SetStateAction<Recording[]>>;
}

const MotionHStack = motion(HStack);
const MotionText = motion(Text);

export const AttachmentsBox = ({
  isOpen,
  recordings,
  setRecordings,
}: AttachmentsBoxProps) => {
  return (
    <Box
      position="fixed"
      bottom="90px" // Adjust this value based on your layout
      left="20px" // Adjust this value based on your layout
      zIndex={9999}
      width="auto"
    >
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
      >
        {isOpen ? (
          <MotionHStack
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            overflowX="auto"
            overflowY="hidden"
            css={{
              "&::-webkit-scrollbar": {
                height: "8px",
              },
              "&::-webkit-scrollbar-track": {
                background: "rgba(0, 0, 0, 0.1)",
              },
              "&::-webkit-scrollbar-thumb": {
                background: "rgba(255, 255, 255, 0.2)",
                borderRadius: "4px",
              },
            }}
          >
            {recordings?.map((recording) => (
              <RecordingItem
                key={recording.id}
                recording={recording}
                recordings={recordings}
                setRecordings={setRecordings}
              />
            ))}
          </MotionHStack>
        ) : (
          <MotionText
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            fontSize="2xs"
            color="gray.300"
          >
            {recordings?.length || 0} Recording
            {recordings?.length > 1 ? "s" : ""} Selected
          </MotionText>
        )}
      </motion.div>
    </Box>
  );
};
