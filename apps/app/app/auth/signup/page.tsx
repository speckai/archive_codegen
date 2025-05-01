"use client";

import { ArrowForwardIcon } from "@chakra-ui/icons";
import { Image, Input, Link, Text, useToast, VStack } from "@chakra-ui/react";
import {
  MotionBox,
  MotionDivider,
  MotionHStack,
  MotionIcon,
  MotionText,
  MotionVStack,
} from "@components/animated";
import { RadialButton } from "@components/radial-button";
import { useAuth } from "@utils/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Login() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSigninHover, setIsSigninHover] = useState(false);
  const [subtitle, setSubtitle] = useState<null | string>(null);
  const toast = useToast();

  const { signInWithGoogle, signUpWithEmail, signInWithGithub } = useAuth();

  async function handleSignInWithGoogle() {
    const { success } = await signInWithGoogle();
    if (success) {
      router.push("/home");
    }
  }

  async function handleSignUpWithEmail() {
    setLoading(true);
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/account/auth/exists?email=${encodeURIComponent(email)}`,
    );
    const data = await response.json();
    const { exists } = data;

    if (exists === true) {
      setSubtitle("signin");
      return;
    } else if (exists === "oauth") {
      console.log("oauth");
      setSubtitle("oauth");
      return;
    } else if (exists === "email_verified") {
      setSubtitle("not-verified");
      return;
    }

    const { user, success, error } = await signUpWithEmail(email, password);
    if (user && !user.user_metadata.email_verified) {
      const emailIdentity = user.identities!.find(
        (identity) => identity.provider === "email",
      );
      const createdAt = new Date(emailIdentity?.created_at || "").getTime();
      const confirmationSentAt = new Date(
        user.confirmation_sent_at || "",
      ).getTime();
      const timeDifferenceInSeconds =
        Math.abs(confirmationSentAt - createdAt) / 1000;

      setSubtitle(timeDifferenceInSeconds > 5 ? "not-verified" : "success");
    } else {
      setSubtitle("success");
    }

    setLoading(false);
  }

  async function handleSignInWithGithub() {
    const { success } = await signInWithGithub();
    if (success) {
      router.push("/home");
    } else {
      console.error("GitHub sign-in error");
    }
  }

  useEffect(() => {
    document.title = "Speck | Login";
  }, []);

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
        <Input
          placeholder="Email"
          onChange={(e) => setEmail(e.target.value)}
          isDisabled={subtitle != null}
        />
        <Input
          type="password"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
          isDisabled={subtitle != null}
        />
        <Input
          type="password"
          placeholder="Confirm Password"
          onChange={(e) => setConfirmPassword(e.target.value)}
          isDisabled={subtitle != null}
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
        {subtitle == "signin" && (
          <Text color="blue.300" fontSize="sm" maxW="300px" textAlign="center">
            You already an have account! Please{" "}
            <Link href="/auth/login" textDecoration="underline">
              Sign in
            </Link>
            .
          </Text>
        )}
        {subtitle == "oauth" && (
          <Text color="red.300" fontSize="sm" maxW="300px" textAlign="center">
            You already have a linked account with this email! Please{" "}
            <Link href="/auth/login" textDecoration="underline">
              Sign in
            </Link>{" "}
            with Google or GitHub.
          </Text>
        )}
        {subtitle == "not-verified" && (
          <Text color="red.300" fontSize="sm" maxW="300px" textAlign="center">
            You've already created an account, but your email was not verified.
            We've sent you a new email!
          </Text>
        )}
        {subtitle == "success" && (
          <Text color="green.300" fontSize="sm" maxW="300px" textAlign="center">
            Your account has been created! Please check your email for a
            verification link.
          </Text>
        )}
        <VStack spacing={4} w="full" mt={2}>
          {subtitle == null && (
            <MotionBox w="full">
              <RadialButton
                onClick={handleSignUpWithEmail}
                borderRadius="lg"
                boxShadow="none"
                w="full"
                bg={["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"]}
                border="1px solid rgba(80, 130, 225, 1)"
                isLoading={loading}
                isDisabled={
                  !email ||
                  !password ||
                  password !== confirmPassword ||
                  password.length < 8
                }
              >
                <MotionHStack
                  h="full"
                  w="full"
                  justifyContent="center"
                  spacing={2}
                  onMouseEnter={() => setIsSigninHover(true)}
                  onMouseLeave={() => setIsSigninHover(false)}
                  py={2}
                  px={4}
                >
                  <MotionText fontSize="13px">Sign Up</MotionText>
                  <MotionIcon
                    as={ArrowForwardIcon}
                    boxSize={4}
                    animate={isSigninHover ? { x: 5 } : { x: 0 }}
                    transition={{ duration: 0.2 }}
                  />
                </MotionHStack>
              </RadialButton>
            </MotionBox>
          )}
          <MotionHStack w="full" spacing={3}>
            <MotionDivider
              initial={{ x: 50, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 1.0 }}
            />
            <MotionText
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 1.3 }}
              color="rgba(255, 255, 255, 0.5)"
              fontSize="xs"
            >
              OR
            </MotionText>
            <MotionDivider
              initial={{ x: -50, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.5, delay: 1.0 }}
            />
          </MotionHStack>
          <MotionBox
            initial={{ y: 10, opacity: 0, filter: "saturate(0)" }}
            animate={{ y: 0, opacity: 1, filter: "saturate(1)" }}
            transition={{ duration: 0.5, delay: 1.4 }}
            w="full"
          >
            <RadialButton
              onClick={handleSignInWithGoogle}
              borderRadius="lg"
              boxShadow="none"
              w="full"
            >
              <MotionHStack w="full" justifyContent="center" py={2} px={4}>
                <Image
                  src="/company-icons/google.png"
                  alt="Google"
                  height="14px"
                  width="auto"
                  filter="invert(0.1)"
                />
                <MotionText fontSize="13px">Sign up with Google</MotionText>
              </MotionHStack>
            </RadialButton>
          </MotionBox>
          <MotionBox
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 1.6 }}
            w="full"
          >
            <RadialButton
              onClick={handleSignInWithGithub}
              borderRadius="lg"
              boxShadow="none"
              w="full"
            >
              <MotionHStack w="full" justifyContent="center" py={2} px={4}>
                <Image
                  src="/company-icons/github.png"
                  alt="GitHub"
                  height="14px"
                  width="auto"
                  filter="invert(1)"
                />
                <MotionText fontSize="13px">Sign up with GitHub</MotionText>
              </MotionHStack>
            </RadialButton>
          </MotionBox>
        </VStack>
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
}
