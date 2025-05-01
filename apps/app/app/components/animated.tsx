import {
  Box,
  Divider,
  Flex,
  HStack,
  Icon,
  Image,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import {
  AnimatePresence as MotionAnimatePresence,
  motion,
} from "framer-motion";

// @ts-ignore
export const MotionBox = motion(Box);
// @ts-ignore
export const MotionVStack = motion(VStack);
// @ts-ignore
export const MotionText = motion(Text);
// @ts-ignore
export const MotionImage = motion(Image);
// @ts-ignore
export const MotionHStack = motion(HStack);
// @ts-ignore
export const MotionFlex = motion(Flex);
// @ts-ignore
export const MotionSpinner = motion(Spinner);
// @ts-ignore
export const MotionIcon = motion(Icon);
// @ts-ignore
export const MotionDivider = motion(Divider);

export function AnimatePresence({ children }: { children: React.ReactNode }) {
  return <MotionAnimatePresence>{children}</MotionAnimatePresence>;
}
