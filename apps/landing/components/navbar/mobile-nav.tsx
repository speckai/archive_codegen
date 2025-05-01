"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
import { IconType } from "react-icons";
import { FaSignInAlt } from "react-icons/fa";
import { IoIosRocket } from "react-icons/io";

interface MobileNavItemProps {
  label: string;
  icon?: IconType;
  children?: Array<{ label: string; href: string }>;
  href?: string;
}

const MobileNavItem = ({
  label,
  icon: Icon,
  children,
  href,
}: MobileNavItemProps) => {
  const { isOpen, onToggle } = useDisclosure();

  return (
    <div className="space-y-4" onClick={children ? onToggle : undefined}>
      <a
        href={href ?? "#"}
        className="py-2 flex justify-between items-center hover:no-underline"
      >
        <div className="flex items-center">
          {Icon && <Icon className="w-4 h-4 mr-3" />}
          <span className="font-semibold text-gray-200">{label}</span>
        </div>
        {children && (
          <ChevronDown
            className={`w-6 h-6 transition-all duration-250 ease-in-out ${isOpen ? "transform rotate-180" : ""}`}
          />
        )}
      </a>

      {isOpen && children && (
        <div className="animate-in fade-in mt-2 pl-4 border-l border-solid border-gray-700 space-y-2">
          {children.map((child) => (
            <a key={child.label} href={child.href} className="py-2 block">
              {child.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
};

function useDisclosure() {
  const [isOpen, setIsOpen] = useState(false);
  const onToggle = () => setIsOpen(!isOpen);
  return { isOpen, onToggle };
}

export default function MobileNav() {
  const [shouldMinimize, setShouldMinimize] = useState(false);

  const handleScroll = () => {
    const position = window.pageYOffset;
    setShouldMinimize(position > window.innerHeight / 10);
  };

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div
      className={`
        bg-[rgba(0,0,0,0.5)] p-4
        w-full md:hidden
        ${shouldMinimize ? "w-[80%] mx-auto mt-2 border rounded-xl" : "w-full mx-auto mt-0 border-b"}
        border-b border-[rgba(255,255,255,0.25)]
        transition-all duration-400 ease
      `}
    >
      {MOBILE_NAV_ITEMS.map((navItem) => (
        <MobileNavItem key={navItem.label} {...navItem} />
      ))}
    </div>
  );
}

const MOBILE_NAV_ITEMS: MobileNavItemProps[] = [
  {
    label: "Pricing",
    href: "/pricing",
    icon: IoIosRocket,
  },
  {
    label: "Login",
    href: "/login",
    icon: FaSignInAlt,
  },
];
