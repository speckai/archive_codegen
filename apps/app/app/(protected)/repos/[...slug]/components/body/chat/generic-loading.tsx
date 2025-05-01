import { MotionFlex, MotionSpinner, MotionText } from "@components/animated";
import { useEffect, useState } from "react";

interface GenericLoadingProps {
  text: string;
}

export default function GenericLoading({ text }: GenericLoadingProps) {
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prevDots) => (prevDots.length >= 3 ? "." : prevDots + "."));
    }, 400);

    return () => clearInterval(interval);
  }, []);

  return (
    <MotionFlex
      direction="column"
      align="center"
      justify="center"
      height="100%"
      width="100%"
      p={4}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <MotionSpinner
        thickness="4px"
        speed="0.65s"
        color="blue.500"
        size="xl"
        mb={4}
        initial={{ scale: 0, y: -20 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      />
      <MotionText
        fontSize="lg"
        fontWeight="medium"
        textAlign="center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        color="gray.300"
      >
        {text}
        {dots}
      </MotionText>
    </MotionFlex>
  );
}
