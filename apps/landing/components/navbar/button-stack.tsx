"use client";

import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { RadialButton } from "../ui/custom/radial-button";

export default function ButtonStack() {
  const [authToken, setAuthToken] = useState<string | undefined>(undefined);

  useEffect(() => {
    const token = document.cookie
      .split("; ")
      .find((row) => row.startsWith("authToken="));
    setAuthToken(token);
  }, []);

  return (
    <div className="items-center hidden md:flex space-x-6">
      <RadialButton
        onClick={() => {
          window.open("https://app.speck.sh", "_blank");
        }}
        rightIcon={ChevronRight}
        size="sm"
        className="text-sm"
        isPulseDisabled={true}
      >
        {authToken ? "Dashboard" : "Start Building"}
      </RadialButton>
    </div>
  );
}
