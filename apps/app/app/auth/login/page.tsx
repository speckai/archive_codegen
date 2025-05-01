"use client";

import { ArrowForwardIcon } from "@chakra-ui/icons";
import { Image, Input, Link, useToast, VStack } from "@chakra-ui/react";
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
  const [isSigninHover, setIsSigninHover] = useState(false);
  const [isSigningInWithEmail, setIsSigningInWithEmail] = useState(false);
  const toast = useToast();

  const { signInWithGoogle, signInWithEmail, signInWithGithub } = useAuth();

  async function handleSignInWithGoogle() {
    const { success } = await signInWithGoogle();
    if (success) {
      router.push("/home");
    }
  }

  async function handleSignInWithEmail() {
    setIsSigningInWithEmail(true);
    const { error } = await signInWithEmail(email, password);
    if (error) {
      toast({
        title: "Error",
        description: error.message,
        status: "error",
      });
    } else {
      router.push("/home");
    }
    setIsSigningInWithEmail(false);
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
          <Image src="/logos/no-bg/speck-logo-1024.webp" alt="logo" />
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
        <Input placeholder="Email" onChange={(e) => setEmail(e.target.value)} />
        <Input
          type="password"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !isSigningInWithEmail &&
              email &&
              password
            ) {
              handleSignInWithEmail();
            }
          }}
        />
        <VStack spacing={4} w="full" mt={2}>
          <MotionBox w="full">
            <RadialButton
              onClick={handleSignInWithEmail}
              borderRadius="lg"
              boxShadow="none"
              w="full"
              bg={["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"]}
              border="1px solid rgba(80, 130, 225, 1)"
              isLoading={isSigningInWithEmail}
              isDisabled={!email || !password}
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
                <MotionText fontSize="13px">Sign In</MotionText>
                <MotionIcon
                  as={ArrowForwardIcon}
                  boxSize={4}
                  animate={isSigninHover ? { x: 5 } : { x: 0 }}
                  transition={{ duration: 0.2 }}
                />
              </MotionHStack>
            </RadialButton>
          </MotionBox>
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
                <MotionText fontSize="13px">Sign in with Google</MotionText>
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
                <MotionText fontSize="13px">Sign in with GitHub</MotionText>
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
        Don't have an account?{" "}
        <Link href="/auth/signup" textDecoration="underline">
          Sign up
        </Link>
      </MotionText>
    </VStack>
  );
}
