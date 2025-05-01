import { useTaskStore } from "@/app/utils/stores/task";
import { VStack } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import ChatInput from "./input";
import MessageItem from "./messages/message";

const ChatPanel = () => {
  const { task } = useTaskStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messageSentSignal, setMessageSentSignal] = useState(0);
  useEffect(() => {
    const scrollContainer = messagesEndRef.current?.parentElement;
    if (scrollContainer) {
      setTimeout(() => {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight + 1000,
          behavior: "smooth",
        });
      }, 750);
    }
  }, [task.chatMessages]);

  return (
    <VStack
      w="full"
      h="full"
      px={1}
      pt={6}
      spacing={2}
      justifyContent="space-between"
    >
      <VStack w="full" h="full" overflowY="scroll">
        {task.chatMessages &&
          task.chatMessages.map((message, index) => {
            return (
              <MessageItem
                key={index}
                message={message}
                isLast={
                  task.chatMessages && index === task.chatMessages.length - 1
                }
              />
            );
          })}

        <div ref={messagesEndRef} />
      </VStack>
      <ChatInput messageSentSignal={messageSentSignal} />
    </VStack>
  );
};

export default function ChatWindow() {
  return (
    <VStack w="full" h="full" zIndex={100000}>
      <ChatPanel />
    </VStack>
  );
}
