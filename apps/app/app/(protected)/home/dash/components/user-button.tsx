"use client";

import {
  Avatar,
  Box,
  Button,
  HStack,
  Icon,
  Link,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  VStack,
} from "@chakra-ui/react";
import { User } from "@supabase/supabase-js";
import { useAuth } from "@utils/auth";
import {
  didUserInstallSpeckGithub,
  validateGithubUser,
} from "@utils/functions/github";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CiLogout, CiSettings } from "react-icons/ci";
import { FaBell } from "react-icons/fa";

interface UserButtonProps {
  user: User | null;
}

const MenuText = ({
  children,
  ...props
}: { children: React.ReactNode } & React.ComponentProps<typeof Text>) => {
  return (
    <Text textAlign="right" px={2} {...props}>
      {children}
    </Text>
  );
};

const CustomMenuItem: React.FC<
  { children: React.ReactNode } & React.ComponentProps<typeof MenuItem>
> = ({ children, ...props }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ x: -5 }}
      transition={{ duration: "0.15", type: "easeInOut" }}
    >
      <MenuItem
        bg="transparent"
        borderTop="1px"
        borderColor="rgba(255, 255, 255, 0.05)"
        justifyContent="flex-end"
        display="flex"
        gap={2}
        py={2}
        fontSize="sm"
        cursor="pointer"
        {...props}
      >
        {children}
      </MenuItem>
    </motion.div>
  );
};

export default function UserButton({ user }: UserButtonProps) {
  const { token, signOut } = useAuth();
  const router = useRouter();
  const [notifications, setNotifications] = useState<string[]>([]);

  const handleSettingsClick = () => {
    router.push("/settings");
  };

  const checkGithubItems = async () => {
    const authStatus = await didUserInstallSpeckGithub(token || "");
    const githubUser = await validateGithubUser(token || "");
    const failures = [];

    if (!authStatus) {
      failures.push("Link GitHub App");
    }
    if (!githubUser) {
      failures.push("Link GitHub Account");
    }
    setNotifications(failures);
  };

  useEffect(() => {
    if (token) {
      checkGithubItems();
    }
  }, [token]);

  return (
    <>
      <Menu placement="bottom-end">
        <MenuButton
          as={Button}
          rounded={"full"}
          variant={"link"}
          cursor={"pointer"}
          position="relative"
        >
          <Avatar size={"sm"} src={user?.user_metadata.avatar_url} />
          {notifications.length > 0 && (
            <Box
              key={notifications.length}
              position="absolute"
              top="-1px"
              right="-1px"
              width="8px"
              height="8px"
              bg="red.500"
              borderRadius="full"
            />
          )}
        </MenuButton>
        <MenuList
          bg="rgba(200, 200, 200, 0.05)"
          backdropFilter="blur(10px)"
          alignItems="flex-end"
          border="1px solid rgba(255, 255, 255, 0.1)"
          pb={0}
        >
          <MenuText fontSize="sm" fontWeight="bold" mb={1}>
            Hi,{" "}
            {user?.user_metadata?.full_name
              ? user?.user_metadata.full_name.split(" ")[0]
              : "friend"}
          </MenuText>
          <MenuText fontSize="xs" color="gray.500" mb={4}>
            {user?.email}
          </MenuText>
          {notifications.length > 0 && (
            <VStack
              spacing={2}
              alignItems="flex-end"
              pr={2}
              mb={4}
              borderTop="1px"
              borderColor="rgba(255, 255, 255, 0.05)"
              w="full"
              pt={2}
            >
              <HStack alignItems="center">
                <FaBell size={12} />
                <Text fontSize="xs" display="flex" alignItems="center">
                  Notifications
                </Text>
              </HStack>
              {notifications.map((notification, index) => (
                <Link
                  href={`/settings`}
                  key={`notification-${index}`}
                  _hover={{
                    textDecoration: "none",
                  }}
                >
                  <Text
                    key={notification}
                    fontSize="xs"
                    color="red.500"
                    display="flex"
                    alignItems="center"
                    _hover={{
                      transform: "translateX(-5px)",
                    }}
                    transition="transform 0.15s ease-in-out"
                  >
                    {notification}
                  </Text>
                </Link>
              ))}
            </VStack>
          )}

          <CustomMenuItem onClick={handleSettingsClick}>
            Settings
            <Icon as={CiSettings} fontSize="sm" />
          </CustomMenuItem>
          <CustomMenuItem onClick={signOut}>
            Logout
            <Icon as={CiLogout} fontSize="sm" />
          </CustomMenuItem>
        </MenuList>
      </Menu>
    </>
  );
}
