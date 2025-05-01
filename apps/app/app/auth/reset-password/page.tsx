"use client";

import { useAuth } from "@/app/utils/auth";
import { ArrowForwardIcon } from "@chakra-ui/icons";
import { Image, Input, Link, Text, useToast, VStack } from "@chakra-ui/react";
import {
  MotionBox,
  MotionHStack,
  MotionIcon,
  MotionText,
  MotionVStack,
} from "@components/animated";
import { RadialButton } from "@components/radial-button";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const ResetPasswordBody = () => {
  const { verifyPasswordResetToken, resetPassword } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();

  const [email, setEmail] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isResetHover, setIsResetHover] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    document.title = "Speck | Reset Password";

    if (isVerifying) {
      return;
    }
    setIsVerifying(true);

    const tokenHash = searchParams.get("token_hash");
    const type = searchParams.get("type");

    if (!tokenHash || !type) {
      toast({
        title: "Invalid reset link",
        status: "error",
        duration: 3000,
      });
      router.push("/auth/login");
      return;
    }

    const verifyToken = async () => {
      const { success, email: userEmail } = await verifyPasswordResetToken(
        tokenHash,
        type,
      );

      if (success && userEmail) {
        setEmail(userEmail);
      } else {
        toast({
          title: "Invalid or expired reset link",
          description: "Please try again",
          status: "error",
          duration: 3000,
        });
        router.push("/auth/login");
      }
      setIsVerifying(false);
    };

    verifyToken();
  }, [searchParams]);

  const handleResetPassword = async () => {
    if (password !== confirmPassword || password.length < 8) {
      return;
    }

    setLoading(true);
    try {
      const { success, error } = await resetPassword(password);

      if (success) {
        toast({
          title: "Password reset successful",
          status: "success",
          duration: 3000,
        });
        router.push("/auth/login");
      } else {
        throw error;
      }
    } catch (error: any) {
      toast({
        title: "Error resetting password",
        description: error?.message,
        status: "error",
        duration: 3000,
      });
    }
    setLoading(false);
  };

  return (
    <VStack
      position="fixed"
      top="50%"
      left="50%"
      transform="translate(-50%, -50%)"
      spacing={4}
      align="center"
      justify="center"
      w="full"
      h="full"
      bg="radial-gradient(circle, rgba(5, 10, 50, 1) 0%, rgba(5, 10, 25, 1) 100%)"
    >
      <VStack mb={12}>
        <MotionBox
          initial={{
            y: -100,
            opacity: 0,
            filter: "saturate(0)",
            height: 170,
            width: 170,
          }}
          animate={{
            y: 0,
            opacity: 1,
            filter: "saturate(1)",
            height: 150,
            width: 150,
          }}
          transition={{ duration: 0.5 }}
          animation="float 3s ease-in-out infinite"
          sx={{
            "@keyframes float": {
              "0%, 100%": { transform: "translateY(0)" },
              "50%": { transform: "translateY(-15px)" },
            },
          }}
          width={150}
          height={150}
        >
          <Image src="/logos/no-bg/speck-logo-512.webp" alt="logo" />
        </MotionBox>
        <MotionText
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          fontSize="4xl"
          fontWeight="bold"
          userSelect="none"
        >
          Speck
        </MotionText>
      </VStack>
      <MotionVStack
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.7 }}
        rounded="lg"
        boxShadow="0 0 30px rgba(0, 0, 0, 0.5)"
        p={8}
        bg="rgba(255, 255, 255, 0.1)"
        border="1px solid rgba(255, 255, 255, 0.1)"
        spacing={4}
        minW="400px"
      >
        {email && (
          <Text color="white" fontSize="sm" textAlign="center">
            Reset password for {email}
          </Text>
        )}
        <Input
          type="password"
          placeholder="New Password"
          onChange={(e) => setPassword(e.target.value)}
        />
        <Input
          type="password"
          placeholder="Confirm New Password"
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
        {password.length > 0 &&
          confirmPassword.length > 0 &&
          password !== confirmPassword && (
            <Text color="red.500" fontSize="xs">
              Passwords do not match
            </Text>
          )}
        {password.length > 0 && password.length < 8 && (
          <Text color="red.500" fontSize="xs" maxW="300px" textAlign="center">
            Password must be at least 8 characters
          </Text>
        )}
        <MotionBox w="full">
          <RadialButton
            onClick={handleResetPassword}
            borderRadius="lg"
            boxShadow="none"
            w="full"
            bg={["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"]}
            border="1px solid rgba(80, 130, 225, 1)"
            isLoading={loading}
            isDisabled={
              !password ||
              !confirmPassword ||
              password !== confirmPassword ||
              password.length < 8
            }
          >
            <MotionHStack
              h="full"
              w="full"
              justifyContent="center"
              spacing={2}
              onMouseEnter={() => setIsResetHover(true)}
              onMouseLeave={() => setIsResetHover(false)}
              py={2}
              px={4}
            >
              <MotionText fontSize="13px">Reset Password</MotionText>
              <MotionIcon
                as={ArrowForwardIcon}
                boxSize={4}
                animate={isResetHover ? { x: 5 } : { x: 0 }}
                transition={{ duration: 0.2 }}
              />
            </MotionHStack>
          </RadialButton>
        </MotionBox>
      </MotionVStack>
      <MotionText
        initial={{ y: -10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 1.8 }}
        fontSize="sm"
        color="rgba(255, 255, 255, 0.4)"
        userSelect="none"
      >
        Already have an account?{" "}
        <Link href="/auth/login" textDecoration="underline">
          Sign in
        </Link>
      </MotionText>
    </VStack>
  );
};

export default function ResetPassword() {
  return (
    <Suspense>
      <ResetPasswordBody />
    </Suspense>
  );
}
