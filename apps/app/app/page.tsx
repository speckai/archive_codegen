"use client";

import { Box } from "@chakra-ui/react";

import { useAuth } from "@utils/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { session, loaded } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loaded) {
      return;
    }

    if (session) {
      router.push("/home");
    } else {
      router.push("/auth/login");
    }
  }, [session, router, loaded]);

  return <Box as="main" h="100vh" overflowY="hidden"></Box>;
}
