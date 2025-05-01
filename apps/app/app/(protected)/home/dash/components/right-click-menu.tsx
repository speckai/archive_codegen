"use client";

import { Button, HStack, MenuItem, MenuList } from "@chakra-ui/react"; // Added Menu components
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { RadialButton } from "@components/radial-button";
import { useEffect, useRef, useState } from "react";
import { FaFolderOpen, FaTrash } from "react-icons/fa";
interface DeleteRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDelete: () => void;
}

const DeleteRepoModal = ({
  isOpen,
  onClose,
  onDelete,
}: DeleteRepoModalProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Delete Repository</ModalHeader>
        <ModalCloseButton />
        <ModalBody>Are you sure you want to delete this repository?</ModalBody>
        <ModalFooter>
          <HStack>
            <RadialButton
              bg={["rgba(255, 50, 50, 1)", "rgba(255, 50, 50, 0.6)"]}
              border="1px solid rgba(255, 50, 50, 0.6)"
              boxShadow="none"
              borderRadius="lg"
              onClick={onDelete}
            >
              Delete
            </RadialButton>
            <Button onClick={onClose}>Cancel</Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

interface RightClickMenuProps {
  isOpen: boolean;
  position: { x: number; y: number };
  onOpen: () => void;
  onDelete: () => void;
}
export default function RightClickMenu({
  isOpen,
  position,
  onOpen,
  onDelete,
}: RightClickMenuProps) {
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [menuHeight, setMenuHeight] = useState(0);

  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (menuRef.current) {
      setMenuHeight(menuRef.current.offsetHeight);
    }
  }, [isOpen]);

  const deletePressed = () => {
    setIsDeleteModalOpen(false);
    onDelete();
  };

  return (
    <>
      <MenuList
        ref={menuRef}
        position="fixed"
        zIndex={50000}
        bg="rgba(50, 50, 50, 0.2)"
        backdropFilter="blur(5px)"
        style={{
          top: `${position.y - menuHeight / 2}px`,
          left: `${position.x + 10}px`,
        }}
        borderRadius="lg"
        p={1}
      >
        <MenuItem
          bg="transparent"
          h="30px"
          fontSize="sm"
          icon={<FaFolderOpen />}
          onClick={onOpen}
          borderRadius="md"
          _hover={{
            bg: "rgba(255, 255, 255, 0.1)",
            transition: "all 0.05s ease-in-out",
          }}
        >
          Open Repo
        </MenuItem>
        <MenuItem
          bg="transparent"
          h="30px"
          fontSize="sm"
          icon={<FaTrash />}
          onClick={() => setIsDeleteModalOpen(true)}
          borderRadius="md"
          _hover={{
            bg: "rgba(255, 50, 50, 0.2)",
            transition: "all 0.05s ease-in-out",
          }}
        >
          Delete Repo
        </MenuItem>
      </MenuList>
      <DeleteRepoModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onDelete={deletePressed}
      />
    </>
  );
}
