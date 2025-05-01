"use client";

import { Spinner, Text, VStack, useToast } from "@chakra-ui/react";
import { useAuth } from "@utils/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
export default function AuthGithubPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [urlParams, setUrlParams] = useState({
    code: "",
    installationId: "",
    setupAction: "",
  });
  const toast = useToast();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setUrlParams({
      code: params.get("code") || "",
      installationId: params.get("installation_id") || "",
      setupAction: params.get("setup_action") || "",
    });
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    setTimeout(() => {
      window.close();
    }, 500);

    // if (urlParams.code && urlParams.installationId) {
    //   const url = new URL(
    //     `${process.env.NEXT_PUBLIC_API_URL}/github/installed`,
    //   );
    //   fetch(url, {
    //     method: "POST",
    //     body: JSON.stringify({
    //       code: urlParams.code,
    //       installation_id: urlParams.installationId,
    //       setup_action: urlParams.setupAction,
    //     }),
    //     headers: {
    //       "Content-Type": "application/json",
    //       Authorization: `Bearer ${token}`,
    //     },
    //   })
    //     .then((res) => res.json())
    //     .then((data) => {
    //       if (data.success) {
    //         window.close();
    //       }

    //       if (!data.success) {
    //         toast({
    //           title: "Error",
    //           description:
    //             "Unable to add GitHub authentication, please go back and reinstall GitHub app.",
    //           status: "error",
    //           duration: null,
    //         });
    //       }
    //     })
    //     .catch((err) => {
    //       console.log(err);
    //       console.log("\n\n\n\n\n\n");
    //     });
    // }
  }, [urlParams, token]);

  return (
    <VStack
      h="100vh"
      overflowY="hidden"
      justifyContent="center"
      alignItems="center"
    >
      <Spinner />
      <Text>Redirecting...</Text>
      <Text>Code: {urlParams.code}</Text>
      <Text>Installation ID: {urlParams.installationId}</Text>
      <Text>Setup Action: {urlParams.setupAction}</Text>
    </VStack>
  );
}
