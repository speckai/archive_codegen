import { Box } from "@chakra-ui/react";
import { DiffEditor } from "@monaco-editor/react";
import { useEffect, useRef } from "react";

interface DiffBoxProps {
  fileName?: string;
  originalFileContents?: string;
  modifiedFileContents?: string;
  height?: string;
}

export default function DiffBox({
  fileName,
  originalFileContents,
  modifiedFileContents,
}: DiffBoxProps) {
  const editorRef = useRef<any>(null);

  // Scroll to bottom when content changes
  useEffect(() => {
    if (editorRef.current) {
      const modifiedEditor = editorRef.current.getModifiedEditor();
      const model = modifiedEditor.getModel();
      if (model) {
        const lineCount = model.getLineCount();
        modifiedEditor.revealLine(lineCount);
      }
    }
  }, [modifiedFileContents]);

  return (
    <Box w="full" h="full" overflow="hidden">
      <DiffEditor
        original={originalFileContents || ""}
        modified={modifiedFileContents || ""}
        language="typescript"
        theme="vs-dark"
        options={{
          readOnly: true,
          renderSideBySide: false,
          minimap: { enabled: false },
        }}
        height="75vh"
        onMount={(editor) => {
          editorRef.current = editor;
          // Initial scroll to bottom
          const modifiedEditor = editor.getModifiedEditor();
          const model = modifiedEditor.getModel();
          if (model) {
            const lineCount = model.getLineCount();
            modifiedEditor.revealLine(lineCount);
          }
        }}
      />
    </Box>
  );
}
