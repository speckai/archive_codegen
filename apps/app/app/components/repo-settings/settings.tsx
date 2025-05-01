import { saveWorkspaceSettings } from "@/app/utils/functions/repos";
import { useTaskStore } from "@/app/utils/stores/task";
import { ArrowBackIcon } from "@chakra-ui/icons";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Select,
  Skeleton,
  Text,
  Tooltip,
  useToast,
} from "@chakra-ui/react";
import { RadialButton } from "@components/radial-button";
import { WorkspaceSettings } from "@ctypes/repos";
import { useAuth } from "@utils/auth";
import { useSocket } from "@utils/socket";
import { useRouter } from "next/navigation";
import { FaSave } from "react-icons/fa";

const InfoTooltip = ({ label }: { label: string }) => (
  <Tooltip label={label} placement="top">
    <Box
      mr={"5px"}
      display="flex"
      alignItems="center"
      justifyContent="center"
      w="20px"
      h="20px"
      borderRadius="full"
      bg="rgba(255, 255, 255, 0.05)"
      border="1px solid rgba(255, 255, 255, 0.1)"
      cursor="pointer"
      _hover={{ bg: "rgba(255, 255, 255, 0.15)" }}
      transition="all 0.3s"
    >
      <Text fontSize="xs" color="gray.300">
        ?
      </Text>
    </Box>
  </Tooltip>
);

interface SettingsFieldProps {
  label: string;
  tooltip?: string;
  width?: string;
  skeletonWidth?: string;
  isLoading?: boolean;
  fromScratch?: boolean;
  children: React.ReactNode;
}

const SettingsField = ({
  label,
  tooltip,
  width = "40%",
  skeletonWidth = "calc(100% - 20px)",
  isLoading,
  children,
  fromScratch = false,
}: SettingsFieldProps) => (
  <FormControl
    display="flex"
    alignItems="center"
    justifyContent="space-between"
    mb={4}
    w="full"
  >
    <FormLabel mb="0" w={width}>
      {label}
    </FormLabel>
    <Box display="flex" alignItems="center" w="40%" justifyContent="flex-end">
      {tooltip && <InfoTooltip label={tooltip} />}
      {isLoading && !fromScratch ? (
        <Skeleton w={skeletonWidth} h="40px" borderRadius="md" />
      ) : (
        children
      )}
    </Box>
  </FormControl>
);

interface SettingsBodyProps {
  localSettings: WorkspaceSettings | null;
  savedSettings: WorkspaceSettings | null;
  setLocalSettings: (localSettings: WorkspaceSettings | null) => void;
  close: () => void;
}

export default function SettingsBody({
  localSettings,
  savedSettings,
  setLocalSettings,
  close,
}: SettingsBodyProps) {
  const { token } = useAuth();
  const { task } = useTaskStore();
  const router = useRouter();
  const { emit } = useSocket();
  const toast = useToast();

  const updateDevCommand = (
    newPackageManager: "npm" | "pnpm" | "yarn" | "bun",
  ) => {
    const commands = {
      npm: "npm run dev",
      pnpm: "pnpm run dev",
      yarn: "yarn dev",
      bun: "bun run dev",
    };
    setLocalSettings(
      localSettings
        ? {
            ...localSettings,
            devCommand: commands[newPackageManager || "npm"],
          }
        : null,
    );
  };

  const onPackageManagerChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPackageManager = e.target.value as "npm" | "pnpm" | "yarn" | "bun";
    if (localSettings) {
      const commands = {
        npm: "npm run dev",
        pnpm: "pnpm run dev",
        yarn: "yarn dev",
        bun: "bun run dev",
      };
      setLocalSettings({
        ...localSettings,
        packageManager: newPackageManager,
        devCommand: commands[newPackageManager],
      });
    }
  };

  const updateSettings = (updates: Partial<WorkspaceSettings>) => {
    setLocalSettings(
      localSettings
        ? {
            ...localSettings,
            ...updates,
          }
        : null,
    );
  };

  const saveSettings = async () => {
    if (task.isInSettingsAgent) {
      emit("requested_settings", {
        settings: {
          packageManager: localSettings?.packageManager || "npm",
          port: localSettings?.port || 3000,
          devCommand: localSettings?.devCommand || "npm run dev",
          installCommand: localSettings?.installCommand || "npm install",
          tsconfig_path: localSettings?.tsconfig_path || null,
        },
      });
      close();
      return;
    }

    if (task.currentWorkspace?.gitRepoId) {
      const response = await saveWorkspaceSettings(
        task.currentWorkspace.gitRepoId,
        task.currentWorkspace.workspaceName || "",
        token || "",
        {
          branch: localSettings?.branch || "main",
          packageManager: localSettings?.packageManager || "npm",
          port: localSettings?.port || 3000,
          devCommand: localSettings?.devCommand || "npm run dev",
          rootDirectory: localSettings?.rootDirectory || "/",
          installCommand: localSettings?.installCommand || "npm install",
          tsconfig_path: localSettings?.tsconfig_path || null,
          workspaceName: localSettings?.workspaceName || "ERROR",
        },
      );
      if (response.success) {
        toast({
          title: "Settings saved",
          description: "Your settings have been saved. Restarting task.",
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        emit("restart_task", {
          task_id: task.taskId,
        });

        close();
      } else {
        toast({
          title: "Failed to save settings",
          description: response.message,
          status: "error",
          duration: 2000,
          isClosable: true,
        });

        console.error("Failed to save repo settings:", response.message);
      }
    }
  };

  const hasUnsavedChanges = () => {
    return (
      localSettings?.branch !== savedSettings?.branch ||
      localSettings?.packageManager !== savedSettings?.packageManager ||
      localSettings?.port !== savedSettings?.port ||
      localSettings?.devCommand !== savedSettings?.devCommand ||
      localSettings?.rootDirectory !== savedSettings?.rootDirectory ||
      localSettings?.installCommand !== savedSettings?.installCommand ||
      localSettings?.tsconfig_path !== savedSettings?.tsconfig_path ||
      localSettings?.workspaceName !== savedSettings?.workspaceName
    );
  };

  const hasBadInput = () => {
    if (task.isInSettingsAgent) {
      return (
        isNaN(localSettings?.port as number) ||
        localSettings?.port === null ||
        (localSettings?.port || 0) < 1000 ||
        (localSettings?.port || 0) > 65535 ||
        localSettings?.devCommand === "" ||
        localSettings?.installCommand === ""
      );
    }

    return (
      isNaN(localSettings?.port as number) ||
      localSettings?.port === null ||
      (localSettings?.port || 0) < 1000 ||
      (localSettings?.port || 0) > 65535 ||
      localSettings?.devCommand === "" ||
      localSettings?.rootDirectory === "" ||
      localSettings?.installCommand === "" ||
      localSettings?.workspaceName === ""
    );
  };

  return (
    <>
      {hasUnsavedChanges() && (
        <Text color="red.500" fontSize="xs">
          You have unsaved changes
        </Text>
      )}

      {task.isInSettingsAgent && (
        <SettingsField
          label="Space Name"
          isLoading={!localSettings}
          width="30%"
          skeletonWidth="150px"
          fromScratch={task.isInSettingsAgent}
        >
          <Input
            placeholder="Workspace Name"
            type="text"
            value={localSettings?.workspaceName || ""}
            onChange={(e) => updateSettings({ workspaceName: e.target.value })}
            isInvalid={localSettings?.workspaceName === ""}
            w="calc(100% - 20px)"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck="false"
            textAlign="right"
          />
        </SettingsField>
      )}

      <SettingsField
        label="Package Manager"
        isLoading={!localSettings}
        width="30%"
        skeletonWidth="150px"
        fromScratch={task.isInSettingsAgent}
      >
        <Select
          value={localSettings?.packageManager || "npm"}
          onChange={onPackageManagerChange}
          width="150px"
          textAlign="right"
        >
          {["npm", "pnpm", "yarn", "bun"].map((pm) => (
            <option key={pm} value={pm}>
              {pm}
            </option>
          ))}
        </Select>
      </SettingsField>

      <SettingsField
        label="Webview Port"
        isLoading={!localSettings}
        width="30%"
        skeletonWidth="200px"
        fromScratch={task.isInSettingsAgent}
      >
        <Input
          type="number"
          value={localSettings?.port || ""}
          isInvalid={
            isNaN(localSettings?.port as number) ||
            localSettings?.port === null ||
            (localSettings?.port ?? 0) < 1000 ||
            (localSettings?.port ?? 0) > 65535
          }
          onChange={(e) => updateSettings({ port: parseInt(e.target.value) })}
          w="200px"
          textAlign="right"
        />
      </SettingsField>

      <SettingsField
        label="Install Command"
        tooltip="Use the command that installs dependencies"
        isLoading={!localSettings}
        fromScratch={task.isInSettingsAgent}
      >
        <Input
          type="text"
          value={localSettings?.installCommand || ""}
          onChange={(e) => updateSettings({ installCommand: e.target.value })}
          isInvalid={localSettings?.installCommand === ""}
          w="calc(100% - 20px)"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck="false"
          textAlign="right"
        />
      </SettingsField>

      <SettingsField
        label="Dev Command"
        tooltip="Use the command that starts the local server"
        isLoading={!localSettings}
        fromScratch={task.isInSettingsAgent}
      >
        <Input
          type="text"
          value={localSettings?.devCommand || ""}
          onChange={(e) => updateSettings({ devCommand: e.target.value })}
          isInvalid={localSettings?.devCommand === ""}
          w="calc(100% - 20px)"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck="false"
          textAlign="right"
        />
      </SettingsField>

      {!task.isInSettingsAgent && (
        <>
          <SettingsField
            label="Root Directory"
            tooltip="The root directory of the site (where your entry package.json is located)"
            isLoading={!localSettings}
            fromScratch={task.isInSettingsAgent}
          >
            <Input
              type="text"
              value={localSettings?.rootDirectory || ""}
              onChange={(e) =>
                updateSettings({ rootDirectory: e.target.value })
              }
              w="calc(100% - 20px)"
              isInvalid={localSettings?.rootDirectory === ""}
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck="false"
              textAlign="right"
            />
          </SettingsField>

          <SettingsField
            label="TSConfig Path"
            tooltip="The path to your tsconfig.json file (optional, leave blank for auto-detection)"
            isLoading={!localSettings}
            fromScratch={task.isInSettingsAgent}
          >
            <Input
              type="text"
              value={localSettings?.tsconfig_path || ""}
              onChange={(e) =>
                updateSettings({ tsconfig_path: e.target.value || null })
              }
              w="calc(100% - 20px)"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck="false"
              textAlign="right"
              placeholder="e.g., /path/to/tsconfig.json"
            />
          </SettingsField>

          <SettingsField
            label="Branch"
            tooltip="The branch to pull from"
            isLoading={!localSettings}
            skeletonWidth="calc(90% - 20px)"
            fromScratch={task.isInSettingsAgent}
          >
            <Select
              value={localSettings?.branch || "main"}
              onChange={(e) => updateSettings({ branch: e.target.value })}
              w="fit-content"
              textAlign="right"
            >
              {localSettings?.availableBranches?.map((branch: string) => (
                <option key={branch} value={branch}>
                  {branch}
                </option>
              ))}
            </Select>
          </SettingsField>
        </>
      )}

      <HStack justifyContent="flex-end" w="full">
        {localSettings?.devCommand === null ||
        localSettings?.packageManager === null ||
        localSettings?.port === null ||
        localSettings?.rootDirectory === null ? (
          <Button
            scrollMarginY={2}
            colorScheme="red"
            leftIcon={<ArrowBackIcon />}
            size="sm"
            onClick={() => {
              router.push("/home");
              close();
            }}
          >
            Back
          </Button>
        ) : null}

        {task.isInSettingsAgent ? (
          <RadialButton
            onClick={() => {
              emit("requested_settings", { settings: {} });
              close();
            }}
            isOutlined
            boxShadow="none"
            border="1px solid rgba(255,100,100,0.4)"
            size="sm"
          >
            Close
          </RadialButton>
        ) : null}

        <RadialButton
          my={2}
          leftIcon={FaSave}
          size="sm"
          isDisabled={!hasUnsavedChanges() || hasBadInput()}
          onClick={() => {
            saveSettings();
            close();
          }}
        >
          Save
        </RadialButton>
      </HStack>
    </>
  );
}
