import { useRecorderStore } from "@/app/utils/stores/recorder";
import {
  Box,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  VStack,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { useState } from "react";
import Actions from "./actions";
import ConsoleLogEntry from "./console-log";

export default function Transcript() {
  const { activeRecording, currentActionIndex } = useRecorderStore();
  const [activeTab, setActiveTab] = useState<"actions" | "console">("actions");

  if (!activeRecording?.events?.length) {
    return null;
  }

  return (
    <motion.div
      layout
      transition={{
        width: { type: "spring", stiffness: 300, damping: 30 },
        layout: { duration: 0.2 },
      }}
    >
      <Box
        bg="rgba(20, 20, 20, 0.7)"
        backdropFilter="blur(10px)"
        borderRadius="xl"
        border="1px solid rgba(255, 255, 255, 0.1)"
        p={2}
        pointerEvents="auto"
        width="100%"
        pt={0}
      >
        <Tabs
          size="sm"
          index={activeTab === "actions" ? 0 : 1}
          onChange={(index) =>
            setActiveTab(index === 0 ? "actions" : "console")
          }
        >
          <TabPanels>
            <TabPanel p={0}>
              <Actions
                events={activeRecording.events}
                currentActionIndex={currentActionIndex}
              />
            </TabPanel>
            <TabPanel p={0}>
              <VStack spacing={0} align="stretch" maxH="200px" overflowY="auto">
                {activeRecording.consoleLogs.map((log, index) => (
                  <ConsoleLogEntry key={index} log={log} />
                ))}
              </VStack>
            </TabPanel>
          </TabPanels>

          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mt={2}
          >
            <TabList w="full">
              <Tab
                w="full"
                bg={
                  activeTab === "actions"
                    ? "radial-gradient(ellipse at bottom center, rgba(100,200,255,0.2) 0%, rgba(0,0,0,0) 70%)"
                    : "rgba(0,0,0,0)"
                }
              >
                Actions
              </Tab>
              <Tab
                w="full"
                bg={
                  activeTab === "console"
                    ? "radial-gradient(ellipse at bottom center, rgba(100,200,255,0.2) 0%, rgba(0,0,0,0) 70%)"
                    : "rgba(0,0,0,0)"
                }
              >
                Console Logs
              </Tab>
            </TabList>
          </Box>
        </Tabs>
      </Box>
    </motion.div>
  );
}
