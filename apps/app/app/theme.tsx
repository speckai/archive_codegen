"use client";

import { extendTheme } from "@chakra-ui/react";
import "@fontsource-variable/figtree";

export const theme = extendTheme({
  config: {
    initialColorMode: "dark",
    useSystemColorMode: false,
  },
  styles: {
    global: () => ({
      body: {
        bg: "rgba(5, 10, 25, 1)",
      },
      "::-webkit-scrollbar": {
        width: "3px",
        height: "3px",
      },
      "::-webkit-scrollbar-track": {
        background: "transparent",
      },
      "::-webkit-scrollbar-thumb": {
        background: "rgba(255, 255, 255, 0.3)",
        borderRadius: "0",
      },
      "::-webkit-scrollbar-thumb:hover": {
        background: "rgba(255, 255, 255, 0.5)",
      },
      "*": {
        scrollbarWidth: "thin",
        scrollbarColor: "rgba(255, 255, 255, 0.3) transparent",
      },
    }),
  },
  fonts: {
    heading: "Figtree Variable, sans-serif",
    body: "Figtree Variable, sans-serif",
  },
});
