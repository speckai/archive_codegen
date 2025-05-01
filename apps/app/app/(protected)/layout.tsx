"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../utils/auth";

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  const router = useRouter();
  const { unauthorized } = useAuth();

  useEffect(() => {
    if (unauthorized) {
      router.push("/auth/login");
    }
  }, [unauthorized]);

  return <>{children}</>;
}
