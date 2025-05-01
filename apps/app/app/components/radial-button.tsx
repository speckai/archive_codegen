import { Box, Button, Icon, IconButton } from "@chakra-ui/react";
import { MotionBox } from "@components/animated";
import { keyframes } from "@emotion/react";
import { useState } from "react";

interface RadialButtonProps {
  children: React.ReactNode;
  isDisabled?: boolean;
  isOutlined?: boolean;
  borderRadius?: string;
  bg?: string[];
  hoveredBg?: string[];
  border?: string;
  boxShadow?: string;
  rightIcon?: React.ElementType | null;
  leftIcon?: React.ElementType | null;
  onClick?: () => void;
  [key: string]: any;
}

const RadialButton = ({
  children,
  isDisabled = false,
  isOutlined = false,
  borderRadius = "full",
  bg = ["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"],
  hoveredBg = ["rgba(100, 160, 255, 0.3)", "rgba(30, 80, 200, 0.3)"],
  border = "1px solid rgba(80, 130, 225, 1)",
  boxShadow = "0px 0px 40px 0px rgba(30, 80, 200, 1)",
  rightIcon = null,
  leftIcon = null,
  leftIconNotAnimated = false,
  rightIconNotAnimated = false,
  rightIconProps = {},
  leftIconProps = {},
  shouldPulse = false,
  isLoading = false,
  onClick = () => {},
  ...props
}: RadialButtonProps) => {
  const [isHovered, setIsHovered] = useState(false);

  const pulseBorder = keyframes`
  0% { box-shadow: 0 0 0 0 ${bg[1]}; }
  35% { box-shadow: 0 0 0 10px rgba(39, 123, 241, 0); }
  50% { box-shadow: 0 0 0 0 rgba(39, 123, 241, 0); }
`;

  return (
    <Box
      position="relative"
      animation={
        !isDisabled && !isOutlined && shouldPulse
          ? `${pulseBorder} 4s infinite`
          : undefined
      }
      borderRadius={borderRadius}
    >
      <Button
        bg={
          isOutlined
            ? "transparent"
            : `radial-gradient(circle at 50% 105%, ${bg[0]}, ${bg[1]})`
        }
        color="white"
        fontWeight="bold"
        borderRadius={borderRadius}
        _hover={{
          bg: isOutlined
            ? `radial-gradient(circle at 50% 95%, ${hoveredBg[0]}, ${hoveredBg[1]})`
            : `radial-gradient(circle at 50% 95%, ${bg[0]}, ${bg[1]})`,
          opacity: 0.8,
        }}
        border={border}
        boxShadow={boxShadow}
        _active={{
          transform: "scale(0.95)",
        }}
        transition="all 0.2s"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        isDisabled={isDisabled}
        onClick={onClick}
        leftIcon={
          leftIcon && leftIconNotAnimated ? <Icon as={leftIcon} /> : undefined
        }
        isLoading={isLoading}
        rightIcon={
          rightIcon && rightIconNotAnimated ? (
            <Icon as={rightIcon} />
          ) : undefined
        }
        {...props}
      >
        {leftIcon && !leftIconNotAnimated && (
          <MotionBox
            as={leftIcon}
            initial={{ width: 0, opacity: 0 }}
            style={{ marginRight: 2 }}
            animate={{
              width: isHovered ? "auto" : 0,
              opacity: isHovered ? 1 : 0,
              marginRight: isHovered
                ? leftIconProps?.animatedMarginRight || 4
                : 0,
            }}
            transition={{ duration: 0.2 }}
            overflow="hidden"
            {...leftIconProps}
          />
        )}
        {children}
        {rightIcon && !rightIconNotAnimated && (
          <MotionBox
            as={rightIcon}
            initial={{ width: 0, opacity: 0 }}
            style={{ marginLeft: 2 }}
            animate={{
              width: isHovered ? "auto" : 0,
              opacity: isHovered ? 1 : 0,
              marginLeft: isHovered
                ? rightIconProps?.animatedMarginLeft || 4
                : 0,
            }}
            transition={{ duration: 0.2 }}
            overflow="hidden"
            {...(rightIconProps && {
              ...Object.fromEntries(
                Object.entries(rightIconProps).filter(
                  ([key]) => key !== "animatedMarginLeft",
                ),
              ),
            })}
          />
        )}
      </Button>
    </Box>
  );
};

interface RadialIconButtonProps {
  icon: React.ElementType;
  isDisabled?: boolean;
  isOutlined?: boolean;
  borderRadius?: string;
  bg?: string[];
  hoveredBg?: string[];
  border?: string;
  boxShadow?: string;
  "aria-label": string;
  onClick?: () => void;
  [key: string]: any;
}

const RadialIconButton = ({
  icon,
  isDisabled = false,
  isOutlined = false,
  borderRadius = "full",
  bg = ["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"],
  hoveredBg = ["rgba(100, 160, 255, 0.3)", "rgba(30, 80, 200, 0.3)"],
  border = "1px solid rgba(80, 130, 225, 1)",
  boxShadow = "0px 0px 40px 0px rgba(30, 80, 200, 1)",
  shouldPulse = false,
  pulseFrequency = 4,
  isLoading = false,
  onClick = () => {},
  ...props
}: RadialIconButtonProps) => {
  let pulseBorder = keyframes`
    0% { box-shadow: 0 0 0 0 ${bg[1]}; }
    35% { box-shadow: 0 0 0 10px rgba(39, 123, 241, 0); }
    50% { box-shadow: 0 0 0 0 rgba(39, 123, 241, 0); }
  `;

  if (pulseFrequency < 4) {
    pulseBorder = keyframes`
      0% { box-shadow: 0 0 0 0 ${bg[1]}; }
      70% { box-shadow: 0 0 0 10px rgba(39, 123, 241, 0); }
      100% { box-shadow: 0 0 0 0 rgba(39, 123, 241, 0); }
    `;
  }

  return (
    <Box
      position="relative"
      animation={
        !isDisabled && !isOutlined && shouldPulse
          ? `${pulseBorder} ${pulseFrequency}s infinite`
          : undefined
      }
      borderRadius={borderRadius}
    >
      <IconButton
        icon={<Icon as={icon} />}
        bg={
          isOutlined
            ? "transparent"
            : `radial-gradient(circle at 50% 50%, ${bg[0]}, ${bg[1]})`
        }
        color="white"
        borderRadius={borderRadius}
        _hover={{
          bg: isOutlined
            ? `radial-gradient(circle at 50% 50%, ${hoveredBg[0]}, ${hoveredBg[1]})`
            : `radial-gradient(circle at 50% 0%, ${bg[0]}, ${bg[1]})`,
          opacity: 0.8,
        }}
        border={border}
        boxShadow={boxShadow}
        _active={{
          transform: "scale(0.9)",
        }}
        transition="all 0.2s"
        isDisabled={isDisabled}
        onClick={onClick}
        isLoading={isLoading}
        {...props}
      />
    </Box>
  );
};

export { RadialButton, RadialIconButton };
