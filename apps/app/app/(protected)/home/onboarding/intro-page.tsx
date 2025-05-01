"use client";

import { Box } from "@chakra-ui/react";
import { MotionBox } from "@components/animated";
import { useState } from "react";

import { ChevronRightIcon } from "@chakra-ui/icons";
import { RadialButton } from "@components/radial-button";
import { HeroSection, WelcomeText } from "./components/hero-section";

interface IntroPageProps {
  onConfirm: () => void;
}

export default function IntroPage({ onConfirm }: IntroPageProps) {
  const [isDeconstructing, setIsDeconstructing] = useState(false);

  const handleGetStarted = () => {
    setIsDeconstructing(true);
    setTimeout(onConfirm, 1500); // Adjust timing as needed
  };

  return (
    <MotionBox
      h="100vh"
      w="100vw"
      maxH="100vh"
      maxW="100vw"
      flexDirection="column"
      justifyContent="center"
      alignItems="center"
      initial={{ opacity: 0 }}
      animate={{
        opacity: isDeconstructing ? 0 : 1,
        scale: isDeconstructing ? 0.95 : 1,
      }}
      transition={{ duration: 0.5 }}
      overflow="visible"
      pt={"30vh"}
      bg="radial-gradient(circle, rgba(5,20,50,0.8) 0%, rgba(0,10,30,0) 70%)"
    >
      <MotionBox
        animate={{
          opacity: isDeconstructing ? 0 : 1,
        }}
        transition={{ duration: 0.5 }}
        h="25%"
      >
        <HeroSection />
      </MotionBox>
      <MotionBox
        animate={{
          opacity: isDeconstructing ? 0 : 1,
        }}
        transition={{ duration: 0.5, delay: 0.1 }}
        h="15%"
        display="flex"
        justifyContent="center"
        alignItems="center"
      >
        <WelcomeText />
      </MotionBox>

      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        width="100%"
      >
        <Box>
          <MotionBox
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2, duration: 0.3 }}
          >
            <RadialButton
              onClick={handleGetStarted}
              py={6}
              px={6}
              rightIcon={ChevronRightIcon}
              shouldPulse
            >
              Get Started
            </RadialButton>
          </MotionBox>
        </Box>
      </Box>
      {/* 
      <MotionBox
        animate={{
          opacity: isDeconstructing ? 0 : 1,
        }}
        transition={{ duration: 0.5, delay: 0.3 }}
        mt={12}
      >
        <ActionButtons />
      </MotionBox> */}
    </MotionBox>
  );
}
