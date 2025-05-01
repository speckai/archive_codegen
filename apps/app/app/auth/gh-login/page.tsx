"use client";

import { Button, Spinner, Text, VStack, useToast } from "@chakra-ui/react";
import { useAuth } from "@utils/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
export default function AuthGithubPage() {
  const { token } = useAuth();
  const [urlParams, setUrlParams] = useState({
    code: "",
    installationId: "",
    setupAction: "",
  });
  const [gettingCode, setGettingCode] = useState(false);
  const toast = useToast();
  const router = useRouter();
  const [message, setMessage] = useState("Authenticating with GitHub...");
  const [didSucceed, setDidSucceed] = useState<boolean | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    console.log("Setting path");
    setUrlParams({
      code: params.get("code") || "",
      installationId: params.get("installation_id") || "",
      setupAction: params.get("setup_action") || "",
    });
  }, []);

  useEffect(() => {
    if (!token || !urlParams.code) {
      return;
    }

    const exchangeCodeForToken = async () => {
      setGettingCode(true);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/github/exchange_code`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              code: urlParams.code,
            }),
          },
        );

        const data = await response.json();

        if (data.success) {
          setMessage("GitHub authentication successful");
          setDidSucceed(true);
          router.push("/settings");
        } else {
          setMessage("GitHub authentication failed.");
          setDidSucceed(false);
        }
      } catch (error) {
        console.error("Authentication error:", error);
        setMessage("An error occurred during authentication.");
        setDidSucceed(false);
      } finally {
        setGettingCode(false);
      }
    };

    exchangeCodeForToken();
  }, [urlParams.code, token, toast]);

  return (
    <VStack
      h="100vh"
      overflowY="hidden"
      justifyContent="center"
      alignItems="center"
    >
      {gettingCode ? <Spinner /> : <Text></Text>}
      <Text>{message}</Text>
      {didSucceed === false && (
        <Button onClick={() => router.back()}>Go back</Button>
      )}
    </VStack>
  );
}
