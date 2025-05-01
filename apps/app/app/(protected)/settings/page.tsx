"use client";

import { ChevronLeftIcon, ExternalLinkIcon } from "@chakra-ui/icons";
import {
  Avatar,
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Image,
  Input,
  Skeleton,
  Spinner,
  Text,
  Textarea,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { MotionBox, MotionVStack } from "@components/animated";
import { RadialButton } from "@components/radial-button";
import { useAuth } from "@utils/auth";
import { updateUserSettings } from "@utils/functions/account";
import {
  getSpeckInstalledOrgs,
  refreshGithubInstallations,
  validateGithubUser,
} from "@utils/functions/github";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FaGithub, FaSave } from "react-icons/fa";
import { SettingsModal } from "./modal";

import {
  getSubscriptionData,
  SubscriptionDetails,
} from "@utils/functions/billing";
import {
  getUserCustomRules,
  saveUserCustomRules,
} from "@utils/functions/repos";

export default function SettingsPage() {
  const router = useRouter();
  const { user, token } = useAuth();
  const toast = useToast();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState(user?.email || "");
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [originalSettings, setOriginalSettings] = useState({
    firstName: "",
    lastName: "",
    email: "",
  });
  const [githubUser, setGithubUser] = useState<string | false | null>(null);
  const [installedOrgs, setInstalledOrgs] = useState<string[] | null>(null);
  const [subscriptionData, setSubscriptionData] =
    useState<SubscriptionDetails | null>(null);
  const [customRules, setCustomRules] = useState<string | null>(null);
  const [originalCustomRules, setOriginalCustomRules] = useState<string>("");
  const [isRefreshingInstallations, setIsRefreshingInstallations] =
    useState(false);

  useEffect(() => {
    if (!user) {
      return;
    }
    setIsLoading(true);

    const name =
      user?.user_metadata?.name ||
      user?.user_metadata?.full_name ||
      user?.user_metadata?.first_name ||
      "";
    const localFirstName = name.split(" ")[0];
    const localLastName = name.split(" ")[1];
    const localEmail = user?.email || "";

    setFirstName(localFirstName);
    setLastName(localLastName);
    setEmail(localEmail);
    setOriginalSettings({
      firstName: localFirstName,
      lastName: localLastName,
      email: localEmail,
    });
    setIsLoading(false);
  }, [user]);

  const hasChanges = () => {
    return (
      firstName !== originalSettings.firstName ||
      lastName !== originalSettings.lastName ||
      email !== originalSettings.email ||
      customRules !== originalCustomRules
    );
  };

  const getChangedFields = () => {
    const changes = [];
    if (firstName !== originalSettings.firstName) {
      changes.push(`First Name: ${originalSettings.firstName} → ${firstName}`);
    }
    if (lastName !== originalSettings.lastName) {
      changes.push(`Last Name: ${originalSettings.lastName} → ${lastName}`);
    }
    if (email !== originalSettings.email) {
      changes.push(`Email: ${originalSettings.email} → ${email}`);
    }
    if (customRules !== originalCustomRules) {
      changes.push(`Custom Rules: ${originalCustomRules} → ${customRules}`);
    }
    return changes;
  };

  const checkIfLinkedToGithub = async () => {
    setGithubUser(null);
    const username = await validateGithubUser(token || "");
    setGithubUser(username || false);
  };

  const handleSave = async () => {
    if (!token) {
      return;
    }

    try {
      await updateUserSettings(firstName, lastName, email);
      await saveUserCustomRules(token, customRules || "");
      setOriginalSettings({ firstName, lastName, email });
      setOriginalCustomRules(customRules || "");
      setIsModalOpen(false);
    } catch (error) {
      console.error("Failed to update settings:", error);
    }
  };

  const handleLinkGithub = () => {
    let redirectUrl = "https://app.speck.sh";
    if (process.env.NEXT_PUBLIC_API_URL?.includes("localhost")) {
      redirectUrl = "http://localhost:3000";
    }

    const url = `https://github.com/login/oauth/authorize?client_id=${process.env.NEXT_PUBLIC_GITHUB_APP_CLIENT_ID}&scope=repo&redirect_uri=${redirectUrl}/auth/gh-login`;
    window.location.href = url;
  };

  const githubAppUrl = `https://github.com/apps/${
    process.env.NEXT_PUBLIC_GITHUB_APP_NAME || "speck-engineer"
  }/installations/select_target`;

  const fetchInstalledOrgs = async () => {
    const installedOrgs = await getSpeckInstalledOrgs(token || "");
    setInstalledOrgs(installedOrgs);
  };

  const fetchCustomRulesUser = async () => {
    const customRules = await getUserCustomRules(token || "");
    setCustomRules(customRules.rules || "");
    setOriginalCustomRules(customRules.rules || "");
  };

  const handleRefreshInstallations = async () => {
    if (!token) return;

    setIsRefreshingInstallations(true);
    try {
      const result = await refreshGithubInstallations(token);
      if (result.success) {
        setInstalledOrgs(result.installations);
        if (result.addedCount > 0) {
          toast({
            title: "Installations refreshed",
            description: `Found ${result.addedCount} new installation${result.addedCount === 1 ? "" : "s"}.`,
            status: "success",
            duration: 5000,
            isClosable: true,
          });
        } else {
          toast({
            title: "Installations refreshed",
            description: "No new installations found.",
            status: "info",
            duration: 3000,
            isClosable: true,
          });
        }
      } else {
        toast({
          title: "Error refreshing installations",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error("Error refreshing installations:", error);
      toast({
        title: "Error refreshing installations",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsRefreshingInstallations(false);
    }
  };

  useEffect(() => {
    if (!token) {
      return;
    }

    checkIfLinkedToGithub();
    fetchInstalledOrgs();
    fetchCustomRulesUser();
    const fetchSubscriptionData = async () => {
      const subscriptionData = await getSubscriptionData(token);
      setSubscriptionData(subscriptionData);
    };

    fetchSubscriptionData();
  }, [token]);

  return (
    <Box
      as="main"
      h="100vh"
      overflowY="auto"
      bg="radial-gradient(circle, rgba(5, 10, 50, 1) 0%, rgba(5, 10, 25, 1) 100%)"
      p={4}
    >
      <MotionVStack
        h="full"
        w="full"
        spacing={4}
        align="start"
        mx="auto"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        alignItems="center"
      >
        <HStack w="full" justifyContent="space-between">
          <RadialButton
            bg={["rgba(255, 100, 100, 1)", "rgba(200, 30, 30, 1)"]}
            hoveredBg={["rgba(255, 100, 100, 0.3)", "rgba(200, 30, 30, 0.3)"]}
            border="1px solid rgba(255, 100, 100, 0.5)"
            boxShadow="none"
            onClick={() => router.push("/")}
            leftIcon={ChevronLeftIcon}
            size="sm"
            borderRadius="lg"
          >
            Back
          </RadialButton>
          <HStack spacing={4} alignItems="center">
            <Text fontSize="md" fontWeight="bold">
              Account Settings
            </Text>
            <Image
              src="/logos/no-bg/speck-logo-512.webp"
              alt="speck"
              width={8}
              height={8}
            />
          </HStack>
        </HStack>

        <MotionBox
          w="full"
          h="full"
          bg="rgba(255, 255, 255, 0.03)"
          backdropFilter="blur(10px)"
          border="1px solid rgba(255, 255, 255, 0.075)"
          borderRadius="xl"
          p={8}
          my={4}
          mx={{ base: 0, md: 12 }}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2, delay: 0.1 }}
        >
          <VStack spacing={6} align="start" w="full">
            <HStack spacing={8} w="full">
              <Avatar
                size="xl"
                name={`${firstName} ${lastName}`}
                src={user?.user_metadata.avatar_url}
                bg="blue.500"
                {...(isLoading && { as: Skeleton })}
              />

              <VStack spacing={4} w="full">
                <HStack w="full" spacing={4}>
                  <FormControl>
                    <FormLabel>First Name</FormLabel>
                    {isLoading ? (
                      <Skeleton>
                        <Input />
                      </Skeleton>
                    ) : (
                      <Input
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        bg="rgba(255, 255, 255, 0.05)"
                        border="1px solid rgba(255, 255, 255, 0.1)"
                      />
                    )}
                  </FormControl>

                  <FormControl>
                    <FormLabel>Last Name</FormLabel>
                    {isLoading ? (
                      <Skeleton>
                        <Input />
                      </Skeleton>
                    ) : (
                      <Input
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        bg="rgba(255, 255, 255, 0.05)"
                        border="1px solid rgba(255, 255, 255, 0.1)"
                      />
                    )}
                  </FormControl>
                </HStack>

                <FormControl>
                  <FormLabel>Email</FormLabel>
                  {isLoading ? (
                    <Skeleton>
                      <Input />
                    </Skeleton>
                  ) : (
                    <Input
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      bg="rgba(255, 255, 255, 0.05)"
                      border="1px solid rgba(255, 255, 255, 0.1)"
                    />
                  )}
                </FormControl>
              </VStack>
            </HStack>
          </VStack>

          <VStack w="full" mt={4} borderRadius="xl">
            <Text textAlign={"left"} fontWeight="bold" w="full">
              Linked Accounts
            </Text>
            <VStack w="full">
              <HStack
                w="full"
                justifyContent="space-between"
                border="1px solid rgba(255, 255, 255, 0.05)"
                borderRadius={"lg"}
                p={4}
                px={6}
              >
                <HStack>
                  <FaGithub />
                  <Text>GitHub</Text>
                </HStack>
                <HStack>
                  {githubUser === false ? (
                    <Button
                      onClick={handleLinkGithub}
                      size="xs"
                      colorScheme="red"
                    >
                      Link
                    </Button>
                  ) : githubUser ? (
                    <HStack spacing={1}>
                      <Text fontSize="xs" color="green.500">
                        Linked to
                      </Text>
                      <Text
                        fontSize="xs"
                        color="green.300"
                        fontWeight="semibold"
                      >
                        {githubUser}
                      </Text>
                      {/* <Button
                        onClick={handleLinkGithub}
                        size="xs"
                        colorScheme="red"
                      >
                        Unlink
                      </Button> */}
                    </HStack>
                  ) : (
                    <Spinner size="xs" />
                  )}
                </HStack>
              </HStack>
            </VStack>
          </VStack>

          <VStack w="full" mt={6} borderRadius="xl">
            <HStack w="full" justifyContent="space-between">
              <Text textAlign={"left"} fontWeight="bold" w="full">
                GitHub Installed Organizations
              </Text>
              <HStack spacing={2}>
                <Button
                  size="xs"
                  variant="ghost"
                  colorScheme="blue"
                  isLoading={isRefreshingInstallations}
                  onClick={handleRefreshInstallations}
                  title="Refresh installations"
                >
                  Refresh
                </Button>
                <Button
                  size="xs"
                  variant={
                    installedOrgs && installedOrgs.length === 0
                      ? "solid"
                      : "ghost"
                  }
                  colorScheme={
                    installedOrgs && installedOrgs.length === 0 ? "red" : "gray"
                  }
                  onClick={() => window.open(githubAppUrl, "_blank")}
                >
                  Add
                  {installedOrgs && installedOrgs.length === 0 ? "" : " more"}
                </Button>
              </HStack>
            </HStack>
            <VStack
              w="full"
              alignItems="flex-start"
              borderRadius="lg"
              border="1px solid rgba(255, 255, 255, 0.05)"
              p={4}
              px={7}
            >
              {installedOrgs === null ? (
                <Spinner size="xs" />
              ) : installedOrgs.length === 0 ? (
                <Text color="red.600" fontWeight="bold">
                  None
                </Text>
              ) : (
                installedOrgs.map((org) => (
                  <Text key={org} fontSize="sm" color="gray.300">
                    {org}
                  </Text>
                ))
              )}
            </VStack>
          </VStack>

          <VStack w="full" mt={6} borderRadius="xl">
            <HStack w="full" justifyContent="space-between">
              <Text textAlign={"left"} fontWeight="bold" w="full">
                Subscription Details
              </Text>
              {subscriptionData?.subscriptionFound && (
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() =>
                    window.open(subscriptionData.manageLink, "_blank")
                  }
                >
                  Manage
                </Button>
              )}
            </HStack>
            <VStack
              w="full"
              alignItems="flex-start"
              borderRadius="lg"
              border="1px solid rgba(255, 255, 255, 0.05)"
              p={4}
              px={7}
              spacing={3}
            >
              {!subscriptionData ? (
                <Spinner size="xs" />
              ) : !subscriptionData.subscriptionFound ? (
                <HStack w="full" justifyContent="space-between">
                  <Text color="rgb(240, 0, 0)" fontSize="sm">
                    No active subscription
                  </Text>
                  <RadialButton
                    size="xs"
                    variant="ghost"
                    onClick={() =>
                      window.open(subscriptionData.subscriptionLink)
                    }
                    rightIcon={ExternalLinkIcon}
                    shouldPulse
                  >
                    Subscribe
                  </RadialButton>
                </HStack>
              ) : (
                <>
                  <HStack w="full" justifyContent="space-between">
                    <Text fontSize="sm" color="gray.400">
                      Next Billing Date
                    </Text>
                    <Text fontSize="sm" fontWeight="semibold">
                      {subscriptionData.nextBillingDate
                        ? new Date(
                            subscriptionData.nextBillingDate * 1000,
                          ).toLocaleDateString()
                        : "N/A"}
                    </Text>
                  </HStack>
                  <HStack w="full" justifyContent="space-between">
                    <Text fontSize="sm" color="gray.400">
                      Subscription Duration
                    </Text>
                    <Text fontSize="sm" fontWeight="semibold">
                      {subscriptionData.daysSubscribed}{" "}
                      {subscriptionData.daysSubscribed === 1 ? "day" : "days"}
                    </Text>
                  </HStack>
                </>
              )}
            </VStack>
          </VStack>

          <VStack w="full" mt={6} borderRadius="xl">
            <HStack justify="space-between" w="full">
              <Text textAlign="left" fontWeight="bold">
                Global Custom Rules
              </Text>
              <Text color="gray.400" textAlign="right" fontSize="xs">
                Custom rules for Speck to follow. These are global and applied
                to all tasks.
              </Text>
            </HStack>
            {customRules !== null ? (
              <Textarea
                value={customRules}
                onChange={(e) => setCustomRules(e.target.value)}
                bg="rgba(255, 255, 255, 0.02)"
                border="1px solid rgba(255, 255, 255, 0.1)"
              />
            ) : (
              <Skeleton h="100px" w="full" borderRadius="lg" />
            )}
          </VStack>

          <MotionBox
            w="full"
            mt={8}
            display="flex"
            justifyContent="flex-end"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.2 }}
          >
            <RadialButton
              onClick={() => setIsModalOpen(true)}
              rightIcon={FaSave}
              rightIconProps={{
                animatedMarginLeft: 8,
                size: "0.9rem",
              }}
              isDisabled={!hasChanges() || isLoading}
              shouldPulse
            >
              Save Changes
            </RadialButton>
          </MotionBox>
        </MotionBox>
      </MotionVStack>

      <SettingsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        changedFields={getChangedFields()}
        onSave={handleSave}
      />
    </Box>
  );
}
