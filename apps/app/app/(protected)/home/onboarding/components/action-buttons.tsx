"use client";

import { HStack, Link, Text, VStack } from "@chakra-ui/react";
import { MotionBox } from "@components/animated";
import { motion } from "framer-motion";
import { HiOutlineDocumentText } from "react-icons/hi";

interface ActionButtonProps {
  href: string;
  icon: React.ElementType;
  title: string;
  description: string;
  delay: number;
}

export const ActionButton = ({
  href,
  icon: Icon,
  title,
  description,
  delay,
}: ActionButtonProps) => (
  <Link href={href} isExternal>
    <MotionBox
      as={motion.button}
      color="white"
      p={4}
      borderRadius="lg"
      boxShadow="md"
      bg="linear-gradient(to bottom, transparent, rgba(10, 60, 100, 0.3))"
      border="1px solid rgba(255,255,255,0.1)"
      maxW="250px"
      maxH="125px"
      initial={{ y: 30, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{
        default: { duration: 0.3, delay },
        scale: { duration: 0.15, delay: 0 },
      }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      position="relative"
      overflow="hidden"
      _before={{
        content: '""',
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        // background:
        //   "linear-gradient(to bottom, transparent, rgba(10, 60, 100, 0.3))",
        zIndex: -1,
        transition: "opacity 0.2s ease-in-out",
      }}
      _after={{
        content: '""',
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background:
          "linear-gradient(to bottom, transparent, rgba(10, 60, 100, 1))",
        zIndex: -1,
        opacity: 0,
        transition: "opacity 0.2s ease-in-out",
      }}
      _hover={{
        "&::before": {
          opacity: 0,
        },
        "&::after": {
          opacity: 1,
        },
      }}
    >
      <VStack spacing={2} align="center">
        <Icon size={24} />
        <Text fontWeight="bold">{title}</Text>
        <Text fontSize="sm" textAlign="center">
          {description}
        </Text>
      </VStack>
    </MotionBox>
  </Link>
);

const ActionButtons = () => (
  <HStack h="full" w="full" spacing={4} justifyContent="center">
    <ActionButton
      href="https://docs.speck.sh/"
      icon={HiOutlineDocumentText}
      title="View Docs"
      description="Read up on how to set up Speck."
      delay={0.9}
    />
  </HStack>
);

export { ActionButtons };
