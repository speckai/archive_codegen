"use client";

import {
  Box,
  Button,
  Popover,
  PopoverAnchor,
  PopoverBody,
  PopoverContent,
  VStack,
} from "@chakra-ui/react";
import { RadialIconButton } from "@components/radial-button";
import { useState } from "react";
import { AiOutlineIssuesClose } from "react-icons/ai";
import { FaPlus } from "react-icons/fa";
import CreateTaskModal from "./create-task/modal";
interface AddDirectoryProps {
  shouldPulse?: boolean;
}
export default function AddDirectory({ shouldPulse }: AddDirectoryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [createTaskModalOpen, setCreateTaskModalOpen] = useState(false);

  const closePopover = () => {
    setIsOpen(false);
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
    }, 100);
  };

  const togglePopover = () => {
    if (isClosing) {
      return;
    }
    setIsOpen(!isOpen);
  };

  return (
    <>
      <Popover isOpen={isOpen} onClose={closePopover} closeOnBlur={true}>
        <PopoverAnchor>
          <RadialIconButton
            size="sm"
            rounded="full"
            colorScheme="blue"
            icon={FaPlus}
            onClick={togglePopover}
            aria-label="Add directory"
            shouldPulse={shouldPulse}
            pulseFrequency={2}
            border="none"
            boxShadow={
              !shouldPulse ? "none" : "0px 0px 30px 0px rgba(30, 80, 200, 1)"
            }
            w="full"
          />
        </PopoverAnchor>
        <PopoverContent
          bg="rgba(100,100,100,0.4)"
          borderWidth={1}
          borderColor="rgba(255,255,255,0.1)"
          backdropFilter="blur(10px)"
          borderRadius="xl"
          w="185px"
          zIndex={1000}
          mr={3}
          mt={-1}
        >
          <PopoverBody p={2}>
            <VStack align="stretch" spacing={2} backdropFilter="blur(10px">
              <Button
                onClick={() => setCreateTaskModalOpen(true)}
                size="sm"
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Box width="20%" display="flex" justifyContent="flex-start">
                  <AiOutlineIssuesClose />
                </Box>
                <Box width="80%" textAlign="left">
                  Create Task
                </Box>
              </Button>
            </VStack>
          </PopoverBody>
        </PopoverContent>
      </Popover>
      <CreateTaskModal
        isOpen={createTaskModalOpen}
        setIsOpen={setCreateTaskModalOpen}
      />
    </>
  );
}
