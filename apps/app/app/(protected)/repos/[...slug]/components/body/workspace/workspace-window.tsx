import { useTaskStore } from "@/app/utils/stores/task";
import { VStack } from "@chakra-ui/react";
import { useState } from "react";
import PlanMain from "../plan/main";

export default function WorkspaceWindow() {
  const [activeTab, setActiveTab] = useState<
    "workspace" | "editor" | "plan" | null
  >(null);
  const { task } = useTaskStore();

  return (
    <VStack w="full" h="full" p={1} overflowY="scroll">
      <PlanMain />
      {/* <Tabs
        w="full"
        h="full"
        display="flex"
        flexDirection="column"
        isFitted
        index={activeTab === "workspace" ? 0 : activeTab === "editor" ? 1 : 2}
        onChange={(index) =>
          setActiveTab(
            index === 0 ? "workspace" : index === 1 ? "editor" : "plan",
          )
        }
        overflowY="scroll"
      >
        <TabList>
          <Tab
            borderBottom="1px solid rgba(255, 255, 255, 0.05)"
            bg={
              activeTab === "workspace"
                ? "radial-gradient(ellipse at 50% 150%, rgba(50, 100, 200, 0.5) 0%, rgba(255, 255, 255, 0) 80%)"
                : "transparent"
            }
          >
            Workspace
          </Tab>
          <Tab
            borderBottom="1px solid rgba(255, 255, 255, 0.05)"
            bg={
              activeTab === "editor"
                ? "radial-gradient(ellipse at 50% 150%, rgba(50, 100, 200, 0.5) 0%, rgba(255, 255, 255, 0) 80%)"
                : "transparent"
            }
          >
            Editor
          </Tab>
          <Tab
            borderBottom="1px solid rgba(255, 255, 255, 0.05)"
            bg={
              activeTab === "plan"
                ? "radial-gradient(ellipse at 50% 150%, rgba(50, 100, 200, 0.5) 0%, rgba(255, 255, 255, 0) 80%)"
                : "transparent"
            }
          >
            Plan
          </Tab>
        </TabList>

        <TabPanels flex={1} display="flex" flexDirection="column">
          <TabPanel h="full" display="flex" flexDirection="column">
            <Box flex={1} overflow="auto">
              <Text>Workspace</Text>
            </Box>
          </TabPanel>
          <TabPanel h="full" p={0} display="flex" flexDirection="column">
            <Box flex={1} overflow="auto">
              <Text>Editor</Text>
            </Box>
            <Box
              h={task?.uiState.terminalShown === true ? "30%" : "40px"}
              transition="height 0.2s ease-out"
            >
              <TerminalWindow />
            </Box>
          </TabPanel>
          <TabPanel h="full" p={0}>
            <PlanMain />
          </TabPanel>
        </TabPanels>
      </Tabs> */}
    </VStack>
  );
}
