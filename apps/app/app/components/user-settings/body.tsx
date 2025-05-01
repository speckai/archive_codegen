import { Box, Button, FormControl } from "@chakra-ui/react";
import { useUserSettingsStore } from "@utils/stores/user-settings";
import { FaSave } from "react-icons/fa";

export default function UserSettingsBody({ close }: { close: () => void }) {
  const { setUserSettings } = useUserSettingsStore();

  return (
    <Box>
      <FormControl
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={4}
      >
        {/* <FormLabel mb="0" mr={2}>
          Editor
        </FormLabel>
        <Select value={editor} onChange={onEditorChange} width="auto">
          <option value="VSCode">VSCode</option>
          <option value="Cursor">Cursor</option>
        </Select> */}
      </FormControl>

      <Box display="flex" justifyContent="flex-end" w="full">
        <Button
          mb={4}
          colorScheme="blue"
          leftIcon={<FaSave />}
          onClick={() => {
            // saveUserSettings();
            close();
          }}
        >
          Save
        </Button>
      </Box>
    </Box>
  );
}
