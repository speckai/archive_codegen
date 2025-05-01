"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { ComponentPropsWithoutRef, useRef, useState } from "react";
import { Button } from "../button";

interface RadialButtonIconProps {
  animatedMarginLeft?: number;
  animatedMarginRight?: number;
  className?: string;
}

interface RadialButtonProps extends ComponentPropsWithoutRef<typeof Button> {
  leftIcon?: React.ElementType;
  leftIconProps?: RadialButtonIconProps;
  leftIconNotAnimated?: boolean;
  rightIcon?: React.ElementType;
  rightIconProps?: RadialButtonIconProps;
  rightIconNotAnimated?: boolean;
  isPulseDisabled?: boolean;
  isOutlined?: boolean;
  bg?: string[];
  border?: string;
  boxShadow?: string;
  isLoading?: boolean;
  onClick?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export function RadialButton({
  leftIcon: LeftIcon,
  leftIconProps,
  leftIconNotAnimated = false,
  rightIcon: RightIcon = ChevronRight,
  rightIconProps,
  rightIconNotAnimated = false,
  isPulseDisabled = false,
  isOutlined = false,
  bg = ["rgba(100, 160, 255, 1)", "rgba(30, 80, 200, 1)"],
  border = "1px solid rgba(80, 130, 225, 1)",
  boxShadow = "0px 0px 40px 0px rgba(30, 80, 200, 1)",
  isLoading = false,
  onClick,
  className,
  children,
  ...props
}: RadialButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={cn(
        "relative rounded-full",
        !isPulseDisabled && !isOutlined && "animate-pulse-radial",
      )}
      style={
        {
          "--pulse-color": bg[1],
        } as React.CSSProperties
      }
    >
      <Button
        ref={buttonRef}
        className={cn(
          "relative overflow-hidden group py-2 pl-4 pr-2",
          isOutlined
            ? "bg-transparent hover:bg-[rgba(100,160,255,0.2)]"
            : "hover:opacity-80 active:scale-95",
          "text-white",
          "rounded-full",
          "transition-all duration-200",
          "text-md",
          // "py-5",
          className,
        )}
        style={{
          background: isOutlined
            ? "transparent"
            : `radial-gradient(circle at 50% ${isHovered ? "95%" : "105%"}, ${bg[0]}, ${bg[1]})`,
          border: border,
          boxShadow: boxShadow,
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={onClick}
        disabled={isLoading}
        {...props}
      >
        {LeftIcon && leftIconNotAnimated && (
          <div className="mr-0 inline-flex items-center justify-center">
            <LeftIcon size="3em" />
          </div>
        )}

        {LeftIcon && !leftIconNotAnimated && (
          <motion.div
            className={cn(
              "inline-flex items-center justify-center overflow-hidden mr-0",
              leftIconProps?.className,
            )}
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: isHovered ? "auto" : 0,
              opacity: isHovered ? 1 : 0,
              marginRight: isHovered
                ? leftIconProps?.animatedMarginRight || 4
                : 0,
            }}
            transition={{ duration: 0.2 }}
          >
            <LeftIcon className="h-4 w-4" />
          </motion.div>
        )}

        <span>{children}</span>

        {RightIcon && rightIconNotAnimated && (
          <div className="ml-2 inline-flex items-center justify-center">
            <RightIcon className="h-4 w-4" />
          </div>
        )}

        {RightIcon && !rightIconNotAnimated && (
          <motion.div
            className={cn(
              "inline-flex items-center justify-center overflow-hidden ml-0",
              rightIconProps?.className,
            )}
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: isHovered ? "auto" : 0,
              opacity: isHovered ? 1 : 0,
              marginLeft: isHovered
                ? rightIconProps?.animatedMarginLeft || 4
                : 0,
            }}
            transition={{ duration: 0.2 }}
          >
            <RightIcon className="h-4 w-4" />
          </motion.div>
        )}
      </Button>
    </div>
  );
}
