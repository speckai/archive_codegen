import { Box, VStack } from "@chakra-ui/react";
import Editor from "./editor";

export default function PlanMain() {
  return (
    <VStack w="full" h="full" p={1} spacing={4}>
      {/* <ButtonGroup size="sm" isAttached variant="outline" w="full">
        <Button
          flex={1}
          onClick={() => updateUIState({ activePlanTab: "editor" })}
          colorScheme={
            task.uiState.activePlanTab === "editor" ? "blue" : "gray"
          }
          bg={
            task.uiState.activePlanTab === "editor"
              ? "radial-gradient(ellipse at 50% 150%, rgba(50, 100, 200, 0.5) 0%, rgba(255, 255, 255, 0) 80%)"
              : "transparent"
          }
          borderWidth={1}
          borderColor="rgba(255, 255, 255, 0.1)"
        >
          Bug Report
        </Button>
        {showIssueTab && (
          <Button
            flex={1}
            onClick={() => updateUIState({ activePlanTab: "issue" })}
            colorScheme={
              task.uiState.activePlanTab === "issue" ? "blue" : "gray"
            }
            bg={
              task.uiState.activePlanTab === "issue"
                ? "radial-gradient(ellipse at 50% 150%, rgba(50, 100, 200, 0.5) 0%, rgba(255, 255, 255, 0) 80%)"
                : "transparent"
            }
            borderWidth={1}
            borderColor="rgba(255, 255, 255, 0.1)"
          >
            Issue
          </Button>
        )}
      </ButtonGroup> */}

      <Box flex={1} w="full" h="full">
        <Box h="full">
          <Editor />
        </Box>
        {/* {task.uiState.activePlanTab === "editor" ? (
          <Box h="full">
            <Editor />
          </Box>
        ) : task.uiState.activePlanTab === "issue" ? (
          <Box h="full">
            {isIssueLoading ? (
              <Center h="full">
                <Flex direction="column" align="center" gap={4}>
                  <Spinner
                    emptyColor="rgba(255,255,255,0.05)"
                    color="rgba(100,200,255,0.7)"
                    size="lg"
                  />
                  <Text color="white" fontSize="lg" fontWeight="medium">
                    Generating issue...
                  </Text>
                </Flex>
              </Center>
            ) : (
              <Text>{task.issue?.content}</Text>
            )}
          </Box>
        ) : null} */}
      </Box>
    </VStack>
  );
}
