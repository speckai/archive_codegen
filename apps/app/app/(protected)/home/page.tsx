"use client";

import { Box } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import Dashboard from "./dash/dashboard";
import IntroPage from "./onboarding/intro-page";

export default function HomePage() {
  const [isFirstTime, setIsFirstTime] = useState<boolean | null>(null);
  const [hasOnboarded, setHasOnboarded] = useState<boolean>(false);

  const confirmOnboarding = () => {
    setHasOnboarded(true);
    localStorage.setItem("hasOnboarded", "true");
  };

  useEffect(() => {
    document.title = "Speck | Dash";
    if (typeof window !== "undefined") {
      const storedValue = localStorage.getItem("hasOnboarded");
      if (storedValue === null) {
        setIsFirstTime(true);
      } else {
        setIsFirstTime(false);
        // setIsFirstTime(true);
      }
    }
  }, []);

  return (
    <>
      {isFirstTime && !hasOnboarded && (
        <Box h="full" w="full">
          <IntroPage onConfirm={confirmOnboarding} />
        </Box>
      )}
      {!isFirstTime || hasOnboarded ? <Dashboard /> : null}
    </>
  );
}
