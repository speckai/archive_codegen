import { useTaskStore } from "@/app/utils/stores/task";
import { Box, Tab, TabList, TabPanel, TabPanels, Tabs } from "@chakra-ui/react";
import { WorkspaceSettings } from "@ctypes/repos";
import { useEffect, useState } from "react";
import CustomRules from "./custom-rules";
import RuntimeFiles from "./runtime-files";
import SettingsBody from "./settings";

interface RepoSettingsBodyProps {
  localSettings: WorkspaceSettings | null;
  setLocalSettings: (localSettings: WorkspaceSettings | null) => void;
  savedSettings: WorkspaceSettings | null;
  close: () => void;
}

export default function RepoSettingsBody({
  localSettings,
  setLocalSettings,
  savedSettings,
  close,
}: RepoSettingsBodyProps) {
  const { task, updateUIState } = useTaskStore();
  const [tabIndex, setTabIndex] = useState(0);

  useEffect(() => {
    if (task.uiState.workspaceSettingsPanelToShow === "settings") {
      setTabIndex(0);
    } else if (task.uiState.workspaceSettingsPanelToShow === "env") {
      setTabIndex(2);
    }
  }, [task.uiState.workspaceSettingsPanelToShow]);

  const handleTabChange = (index: number) => {
    setTabIndex(index);

    const panelMap = {
      0: "settings",
      1: "settings",
      2: "env",
    } as const;

    updateUIState({
      workspaceSettingsPanelToShow: panelMap[index as keyof typeof panelMap],
    });
  };

  return (
    <Box>
      <Tabs index={tabIndex} onChange={handleTabChange}>
        {!task.isInSettingsAgent && (
          <TabList>
            <Tab>Settings</Tab>
            <Tab>Custom Rules</Tab>
            <Tab>Runtime Files</Tab>
          </TabList>
        )}

        <TabPanels>
          <TabPanel>
            <SettingsBody
              localSettings={localSettings}
              savedSettings={savedSettings}
              setLocalSettings={setLocalSettings}
              close={close}
            />
          </TabPanel>

          <TabPanel>
            <CustomRules />
          </TabPanel>

          <TabPanel>
            <RuntimeFiles close={close} />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
}
