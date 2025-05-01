"use client";

import { ChakraProvider } from "@chakra-ui/react";
import "@fontsource-variable/figtree";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";
import { theme } from "./theme";

if (typeof window !== "undefined") {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY as string, {
    api_host: "/ingest",
    person_profiles: "identified_only",
  });
}

const queryClient = new QueryClient();

interface ProvidersProps {
  children: React.ReactNode;
}

export const Providers: React.FC<ProvidersProps> = ({ children }) => {
  return (
    <PostHogProvider client={posthog}>
      <ChakraProvider theme={theme}>
        <QueryClientProvider client={queryClient}>
          {children as React.ReactNode}
        </QueryClientProvider>
      </ChakraProvider>
    </PostHogProvider>
  );
};
