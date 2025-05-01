"use client";

import { HStack } from "@chakra-ui/react";
import { MotionBox, MotionImage, MotionText } from "@components/animated";
import { keyframes } from "@emotion/react";

const gradientAnimation = keyframes`
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
`;

const HeroSection = () => (
  <HStack h="full" w="full" justify="center" align="center" spacing={8}>
    <MotionText
      fontSize={{ base: "xl", sm: "2xl", md: "3xl", lg: "4xl", xl: "5xl" }}
      fontWeight="bold"
      initial={{ x: -50, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      Welcome to{" "}
      <MotionText
        as="span"
        bgGradient="linear(to-r, rgba(80, 130, 225, 1), rgba(30, 80, 200, 1), rgba(80, 130, 225, 1))"
        bgClip="text"
        backgroundSize="200% 100%"
        animation={`${gradientAnimation} 3s linear infinite`}
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        Speck
      </MotionText>
    </MotionText>
    <MotionBox
      maxW={50}
      minW={20}
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      <MotionImage
        src="/logos/no-bg/speck-logo-1024.webp"
        alt="Speck"
        whileHover={{ rotate: 5 }}
        draggable={false}
      />
    </MotionBox>
  </HStack>
);

const WelcomeText = () => (
  <MotionText
    h="full"
    w="full"
    maxW={"5xl"}
    px={20}
    pt={{ base: 0, sm: 0, md: 2, lg: 4 }}
    textAlign="center"
    fontSize={{ base: "sm", sm: "sm", md: "md", lg: "lg" }}
    initial={{ y: 20, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ duration: 0.5, delay: 0.5 }}
  >
    We&apos;re improving Speck&apos;s capabilities every day. If you have any
    questions or feedback, feel free to reach out to us.
  </MotionText>
);

export { HeroSection, WelcomeText };
