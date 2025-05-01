import { RadialButton } from "@/app/components/radial-button";
import {
  Box,
  Button,
  HStack,
  Image,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { AnimatePresence, motion } from "framer-motion";
import { ReactNode, useEffect, useState } from "react";

interface BaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (annotation: string) => void;
  title: string;
  description?: string;
  content?: ReactNode;
  cancelButtonText?: string;
  saveButtonText?: string;
  textareaPlaceholder?: string;
  requireAnnotation?: boolean;
  showLogo?: boolean;
}

export default function BaseModal({
  isOpen,
  onClose,
  onSave,
  title,
  description,
  content,
  cancelButtonText = "Cancel",
  saveButtonText = "Save",
  textareaPlaceholder = "Add your annotation...",
  requireAnnotation = true,
  showLogo = true,
}: BaseModalProps) {
  const [annotation, setAnnotation] = useState("");

  useEffect(() => {
    if (isOpen) {
      setAnnotation("");
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 1001,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "auto",
          }}
        >
          <motion.div
            initial={{ backdropFilter: "blur(0px)" }}
            animate={{ backdropFilter: "blur(4px)" }}
            exit={{ backdropFilter: "blur(0px)" }}
            transition={{ duration: 0.2 }}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0)",
            }}
          >
            <motion.div
              initial={{ backgroundColor: "rgba(0, 0, 0, 0)" }}
              animate={{ backgroundColor: "rgba(0, 0, 0, 0.2)" }}
              exit={{ backgroundColor: "rgba(0, 0, 0, 0)" }}
              transition={{ duration: 0.2 }}
              style={{
                width: "100%",
                height: "100%",
              }}
            />
          </motion.div>

          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            style={{ width: "90%", maxWidth: "600px", position: "relative" }}
          >
            <VStack
              bg="rgba(20, 20, 20, 0.5)"
              p={4}
              borderRadius="lg"
              spacing={4}
              w="full"
              border="1px solid rgba(255, 255, 255, 0.06)"
              backdropFilter="blur(10px)"
            >
              <HStack w="full" justifyContent="center" spacing={4}>
                {showLogo && (
                  <Image
                    src="/logos/no-bg/speck-logo-512.webp"
                    alt="Speck Logo"
                    boxSize={4}
                    zIndex={1000}
                  />
                )}
                <Text fontSize="md" color="gray.200" fontWeight="bold">
                  {title}
                </Text>
              </HStack>

              {description && (
                <Text fontSize="sm" color="gray.400" textAlign="center">
                  {description}
                </Text>
              )}

              {content && <Box w="full">{content}</Box>}

              <Textarea
                value={annotation}
                onChange={(e) => setAnnotation(e.target.value)}
                placeholder={textareaPlaceholder}
                size="md"
                resize="none"
                rows={4}
                border="1px solid rgba(255, 255, 255, 0.05)"
                _focus={{
                  border: "1px solid rgba(66, 153, 225, 0.6)",
                  boxShadow: "0 0 0 1px rgba(66, 153, 225, 0.6)",
                }}
                _hover={{
                  borderColor: "rgba(255, 255, 255, 0.2)",
                }}
              />

              <HStack spacing={2} w="full" justifyContent="flex-end">
                <Button size="sm" variant="ghost" onClick={onClose}>
                  {cancelButtonText}
                </Button>
                <RadialButton
                  size="sm"
                  onClick={() => onSave(annotation)}
                  isDisabled={requireAnnotation && !annotation.trim()}
                >
                  {saveButtonText}
                </RadialButton>
              </HStack>
            </VStack>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
