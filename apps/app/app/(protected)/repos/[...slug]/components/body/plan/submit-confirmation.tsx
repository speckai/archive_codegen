import { RadialButton } from "@/app/components/radial-button";
import { Box, Button, Text } from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "@components/modal";
import { BugReport } from "@ctypes/bug-report";
import { ComponentProps } from "react";
import ReactMarkdown, { Options } from "react-markdown";
import ConsoleLogViewer from "./console-log-viewer";
import { AssetRenderer } from "./editor";
import { customStyles } from "./styles";

interface SubmitConfirmationProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  markdown: string;
  bugReport: BugReport;
}

export default function SubmitConfirmation({
  isOpen,
  onClose,
  onSubmit,
  markdown,
  bugReport,
}: SubmitConfirmationProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" isCentered>
      <ModalOverlay />
      <ModalContent bg="rgba(0,0,0,0.3)" color="white">
        <ModalHeader>Confirm Changes</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Text mb={4}>Please review your changes before submitting:</Text>
          <Box
            p={4}
            borderRadius="lg"
            maxH="60vh"
            overflowY="auto"
            className="mdx-editor"
            bg="rgba(0,0,0,0.7)"
            border="1px solid rgba(255,255,255,0.1)"
          >
            <Box className="prose max-w-none">
              <style>{customStyles}</style>
              <ReactMarkdown
                components={
                  {
                    code: ({ children, ...props }: ComponentProps<"code">) => (
                      <code
                        {...props}
                        style={{
                          backgroundColor: "rgba(255, 255, 255, 0.1)",
                          padding: "0.2em 0.4em",
                          borderRadius: "3px",
                          fontFamily: "monospace",
                          whiteSpace: "pre-wrap",
                          color: "#ffffff",
                        }}
                      >
                        {children}
                      </code>
                    ),
                    h1: ({ children, ...props }: ComponentProps<"h1">) => (
                      <h1
                        {...props}
                        style={{
                          color: "#63b3ed",
                          fontSize: "2em",
                          fontWeight: 700,
                          marginTop: "1.5em",
                          marginBottom: "0.75em",
                        }}
                      >
                        {children}
                      </h1>
                    ),
                    h2: ({ children, ...props }: ComponentProps<"h2">) => (
                      <h2
                        {...props}
                        style={{
                          color: "#ffffff",
                          fontSize: "1.5em",
                          fontWeight: 600,
                          marginTop: "1.25em",
                          marginBottom: "0.5em",
                        }}
                      >
                        {children}
                      </h2>
                    ),
                    img: ({ src, alt }) => {
                      if (
                        src?.startsWith("console_log_") &&
                        bugReport?.textModels[src]
                      ) {
                        return (
                          <ConsoleLogViewer
                            key={src}
                            logData={bugReport.textModels[src]}
                          />
                        );
                      }

                      const assetUrl = bugReport?.assetUrls[src || ""] || src;
                      if (assetUrl) {
                        const isVideo =
                          assetUrl.includes(".webm") ||
                          assetUrl.includes(".mp4");
                        return (
                          <AssetRenderer
                            assetUrl={assetUrl}
                            assetType={isVideo ? "video" : "image"}
                            altText={alt}
                          />
                        );
                      }

                      return null;
                    },
                    p: ({ children, ...props }: ComponentProps<"p">) => (
                      <p
                        {...props}
                        style={{
                          color: "#ffffff",
                          marginBottom: "1em",
                        }}
                      >
                        {children}
                      </p>
                    ),
                  } as Options["components"]
                }
              >
                {markdown}
              </ReactMarkdown>
            </Box>
          </Box>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <RadialButton colorScheme="blue" onClick={onSubmit}>
            Confirm & Submit
          </RadialButton>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
