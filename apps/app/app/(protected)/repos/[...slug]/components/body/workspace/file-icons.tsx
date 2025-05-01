import { Icon } from "@chakra-ui/react";
import { FaJs, FaReact } from "react-icons/fa";
import {
  SiCss3,
  SiDotenv,
  SiHtml5,
  SiJavascript,
  SiJson,
  SiMdx,
  SiTypescript,
} from "react-icons/si";
import { VscMarkdown } from "react-icons/vsc";

interface FileIconProps {
  filename: string;
  [key: string]: any;
}

export const FileIcon = ({ filename, ...props }: FileIconProps) => {
  filename = filename.replace(/\s+/g, "");
  filename = filename.toLowerCase();

  if (filename.endsWith(".jsx")) {
    return <Icon as={FaReact} color="blue.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".tsx")) {
    return <Icon as={SiTypescript} color="blue.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".js")) {
    return <Icon as={SiJavascript} color="yellow.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".ts")) {
    return <Icon as={SiTypescript} color="blue.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".json")) {
    return <Icon as={SiJson} color="green.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".md")) {
    return <Icon as={VscMarkdown} color="purple.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".mjs")) {
    return <Icon as={FaJs} color="white.300" mr={2} {...props} />;
  }

  if (filename.endsWith(".css")) {
    return <Icon as={SiCss3} color="blue.500" mr={2} {...props} />;
  }

  if (filename.includes(".env")) {
    return <Icon as={SiDotenv} color="gray.500" mr={2} {...props} />;
  }

  if (filename.endsWith(".html")) {
    return <Icon as={SiHtml5} color="orange.500" mr={2} {...props} />;
  }

  if (filename.endsWith(".mdx")) {
    return <Icon as={SiMdx} color="purple.500" mr={2} {...props} />;
  }

  return null;
};
