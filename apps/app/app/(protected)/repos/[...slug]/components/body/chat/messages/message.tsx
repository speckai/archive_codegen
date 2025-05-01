import { Recording } from "@/app/types/recording";
import { useTaskStore } from "@/app/utils/stores/task";
import {
  Button as ChakraButton,
  HStack,
  Image,
  Input,
  Text,
  Tooltip,
  VStack,
  Wrap,
} from "@chakra-ui/react";
import {
  Button,
  ButtonAction,
  ChatMessage,
  ChatMessageRole,
} from "@ctypes/chat-message";
import { Image as ImageType } from "@ctypes/image";
import { useSocket } from "@utils/socket";
import { useEffect, useRef, useState } from "react";
import MessageBase from "./message-base";

const ImagePreview = ({ image }: { image: ImageType }) => {
  const [placement, setPlacement] = useState<"top" | "bottom">("top");
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const rect = imageRef.current?.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    setPlacement(rect?.top && rect.top > windowHeight * 0.7 ? "top" : "bottom");
  }, [isOpen]);

  return (
    <Tooltip
      label={
        <Image
          src={image.previewUrl}
          alt={image.name}
          maxH="400px"
          maxW="400px"
          objectFit="contain"
        />
      }
      hasArrow
      placement={placement}
      isOpen={isOpen}
      onOpen={() => setIsOpen(true)}
      onClose={() => setIsOpen(false)}
    >
      <Image
        src={image.previewUrl}
        alt={image.name}
        w="auto"
        h="40px"
        borderRadius="md"
        cursor="pointer"
        ref={imageRef}
      />
    </Tooltip>
  );
};

interface MessageItemProps {
  message: ChatMessage;
  isLast?: boolean;
}
export default function MessageItem({ message, isLast }: MessageItemProps) {
  const [answers, setAnswers] = useState<string[]>(
    () => message.messageData.questions?.map(() => "") || [],
  );
  const { emit } = useSocket();
  const [hasSubmittedQuestions, setHasSubmittedQuestions] = useState(false);
  const { updateUIState, addNewMessage, updateLastChatMessage } =
    useTaskStore();

  useEffect(() => {
    setAnswers(
      message.messageData.questions?.map((question) => question.answer ?? "") ||
        [],
    );
    setHasSubmittedQuestions(
      message.messageData.questions?.some((q) => q.answer) || false,
    );
  }, [message.messageData.questions]);

  const setInputValue = (index: number, value: string) => {
    setAnswers((prevAnswers) => {
      const newAnswers = [...prevAnswers];
      newAnswers[index] = value;
      return newAnswers;
    });
  };

  const handleSubmitAnswers = () => {
    const questionsAndAnswers = answers.map((answer, index) => ({
      question: message.messageData.questions?.[index].question,
      answer,
    }));
    emit("submit_answers", {
      questions_and_answers: questionsAndAnswers,
    });
    setHasSubmittedQuestions(true);
    addNewMessage({
      role: ChatMessageRole.USER,
      messageData: {
        mainMessage: {
          message: `Sent ${answers.length} answers`,
          isItalic: true,
        },
      },
    });
  };

  const handleButtonClick = async (button: Button) => {
    if (!button.action) {
      updateLastChatMessage({
        messageData: {
          ...message.messageData,
          attachments: {
            ...message.messageData.attachments,
            buttons:
              message.messageData.attachments?.buttons?.map((b) =>
                b.label === button.label
                  ? { ...b, clicked: true }
                  : { ...b, clicked: false },
              ) || [],
          },
        },
      });

      emit("submit_button", {
        button_clicked: button.value,
      });
    } else if (button.action === ButtonAction.YES_NO) {
      console.warn("yes no button");
    } else if (button.action === ButtonAction.OPEN_GIT_PANEL) {
      updateUIState({
        gitPanelActive: true,
      });
    } else if (button.action === ButtonAction.OPEN_SETTINGS_PANEL) {
      updateUIState({
        isWorkspaceSettingsModalOpen: true,
        workspaceSettingsPanelToShow: "settings",
      });
    }
  };

  const getButtonColorScheme = (button: Button): string => {
    if (button.action === ButtonAction.ADD_PAGE_TO_CONTEXT) {
      return "blue";
    }
    return button.clicked === null || button.clicked ? "blue" : "gray";
  };

  const isButtonDisabled = (button: Button): boolean => {
    // For SELECT_COMPONENTS and ADD_PAGE_TO_CONTEXT buttons, check if there's a newer message with the same button type
    if (
      button.action === ButtonAction.SELECT_COMPONENTS ||
      button.action === ButtonAction.ADD_PAGE_TO_CONTEXT
    ) {
      const { task } = useTaskStore.getState();
      const currentMessageIndex = task.chatMessages?.findIndex(
        (msg) => msg === message,
      );
      if (currentMessageIndex === undefined || currentMessageIndex === -1) {
        return false;
      }

      const hasNewerSameButton = task.chatMessages
        ?.slice(currentMessageIndex + 1)
        .some((msg) =>
          msg.messageData.attachments?.buttons?.some(
            (b) => b.action === button.action,
          ),
        );

      if (hasNewerSameButton) {
        return true;
      }

      if (button.action === ButtonAction.SELECT_COMPONENTS) {
        return false;
      }
    }

    return button.clicked !== null;
  };

  return (
    <MessageBase message={message} isLast={isLast}>
      <VStack
        w="full"
        spacing={3}
        align={
          message.role === ChatMessageRole.USER ? "flex-end" : "flex-start"
        }
        mt={2}
      >
        {/* MAIN MESSAGE */}
        {message.messageData.mainMessage && (
          <Text
            fontSize="sm"
            whiteSpace="pre-wrap"
            color="white"
            fontStyle={
              message.messageData.mainMessage?.isItalic ? "italic" : "normal"
            }
            maxW="100%"
            // textAlign={message.role === ChatMessageRole.USER ? "right" : "left"}
          >
            {message.messageData.mainMessage?.message &&
              message.messageData.mainMessage?.message
                .split("**")
                .map((part, index) =>
                  index % 2 === 0 ? (
                    part.split("```").map((codePart, codeIndex) =>
                      codeIndex % 2 === 0 ? (
                        // Split non-code parts by URLs and render links
                        codePart
                          .split(/(https?:\/\/[^\s]+)/g)
                          .map((text, linkIndex) =>
                            text.match(/^https?:\/\//) ? (
                              <Text
                                as="a"
                                key={`link-${linkIndex}`}
                                href={text}
                                color="blue.300"
                                textDecoration="underline"
                                target="_blank"
                                rel="noopener noreferrer"
                                display="inline"
                              >
                                {text}
                              </Text>
                            ) : (
                              text
                            ),
                          )
                      ) : (
                        <Text
                          key={`code-${codeIndex}`}
                          p={2}
                          border="1px"
                          borderColor="rgba(255,255,255,0.1)"
                          borderRadius="md"
                          bg="rgba(255,255,255,0.05)"
                          my={2}
                          mr={4}
                          w="full"
                          fontSize="xs"
                        >
                          {codePart.trimStart()}
                        </Text>
                      ),
                    )
                  ) : (
                    <strong key={index}>{part}</strong>
                  ),
                )}
          </Text>
        )}

        {/* QUESTIONS */}
        {message.messageData.questions?.length && (
          <VStack w="full" spacing={3} align="flex-start">
            {message.messageData.questions?.map((question, index) => (
              <VStack key={index} w="full" spacing={1} align="flex-start">
                <Text w="full" fontSize="xs" color="gray.200" ml={2}>
                  {question.question}
                </Text>
                <Input
                  // w="full"
                  maxW="50vw"
                  size="xs"
                  color="white"
                  borderRadius="md"
                  placeholder="Enter your answer"
                  p={3}
                  value={answers[index]}
                  onChange={(e) => setInputValue(index, e.target.value)}
                  isDisabled={hasSubmittedQuestions}
                />
              </VStack>
            ))}
            <HStack spacing={2}>
              <ChakraButton
                size="xs"
                colorScheme="blue"
                onClick={handleSubmitAnswers}
                isDisabled={!answers.every((answer) => answer.trim() !== "")}
                display={
                  hasSubmittedQuestions || !message.messageData.questions
                    ? "none"
                    : "flex"
                }
              >
                Submit
              </ChakraButton>
            </HStack>
          </VStack>
        )}

        {/* ATTACHMENTS */}
        {message.messageData.attachments?.keyValuePairs?.length &&
          message.messageData.attachments?.keyValuePairs?.length > 0 && (
            <VStack
              w="calc(100% - 12px)"
              spacing={1}
              align="flex-start"
              borderWidth={1}
              borderColor="rgba(255,255,255,0.05)"
              bg="rgba(255,255,255,0.04)"
              borderRadius="md"
              p={2}
            >
              {message.messageData.attachments?.keyValuePairs?.map((pair) => (
                <HStack key={pair.key} spacing={1} align="flex-start">
                  <Text fontSize="xs" fontWeight="bold" color="white">
                    {pair.key}:
                  </Text>
                  <Text fontSize="xs" color="white">
                    {pair.value}
                  </Text>
                </HStack>
              ))}
            </VStack>
          )}

        {message.messageData.attachments?.images?.length &&
          message.messageData.attachments?.images?.length > 0 &&
          message.messageData.attachments?.images?.map((image: ImageType) => (
            <ImagePreview key={image.id} image={image} />
          ))}

        <HStack w="full" spacing={1} align="flex-end" justify="flex-end">
          {message.messageData.attachments?.recordings?.length &&
            message.messageData.attachments?.recordings?.length > 0 &&
            message.messageData.attachments?.recordings?.map(
              (recording: Recording) => (
                <Text key={recording.id}>{recording.id}</Text>
              ),
            )}
        </HStack>

        {message.messageData.attachments?.buttons?.length &&
          message.messageData.attachments?.buttons?.length > 0 && (
            <Wrap w="full" spacing={2} align="flex-start">
              {message.messageData.attachments?.buttons?.map((button) => (
                <ChakraButton
                  key={button.label}
                  size="xs"
                  colorScheme={getButtonColorScheme(button)}
                  isDisabled={isButtonDisabled(button)}
                  onClick={() => handleButtonClick(button)}
                >
                  {button.label}
                </ChakraButton>
              ))}
            </Wrap>
          )}
      </VStack>
    </MessageBase>
  );
}
