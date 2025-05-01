import {
  Popover as ChakraPopover,
  PopoverBody as ChakraPopoverBody,
  PopoverCloseButton as ChakraPopoverCloseButton,
  PopoverContent as ChakraPopoverContent,
  PopoverFooter as ChakraPopoverFooter,
  PopoverHeader as ChakraPopoverHeader,
  PopoverTrigger as ChakraPopoverTrigger,
} from "@chakra-ui/react";

const Popover = (props: React.ComponentProps<typeof ChakraPopover>) => (
  <ChakraPopover {...props} />
);

const PopoverTrigger = ChakraPopoverTrigger;

const PopoverContent = (
  props: React.ComponentProps<typeof ChakraPopoverContent>,
) => (
  <ChakraPopoverContent
    bg="rgba(50,50,50,1)"
    borderWidth={1}
    borderColor="rgba(255,255,255,0.1)"
    backdropBlur="10px"
    borderRadius="xl"
    zIndex={9999}
    {...props}
  />
);

const PopoverHeader = (
  props: React.ComponentProps<typeof ChakraPopoverHeader>,
) => <ChakraPopoverHeader {...props} />;

const PopoverBody = (props: React.ComponentProps<typeof ChakraPopoverBody>) => (
  <ChakraPopoverBody {...props} />
);

const PopoverCloseButton = (
  props: React.ComponentProps<typeof ChakraPopoverCloseButton>,
) => <ChakraPopoverCloseButton {...props} />;

const PopoverFooter = (
  props: React.ComponentProps<typeof ChakraPopoverFooter>,
) => <ChakraPopoverFooter {...props} />;

export {
  Popover,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverFooter,
  PopoverHeader,
  PopoverTrigger,
};
