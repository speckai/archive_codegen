"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface DesktopSubNavProps {
  label: string;
  href: string;
  subLabel: string;
}

const DesktopSubNav = ({ label, href, subLabel }: DesktopSubNavProps) => {
  return (
    <a
      href={href}
      role="group"
      className="block p-2 rounded-md hover:bg-gray-900 transition-all duration-200"
    >
      <div className="flex items-center">
        <div className="flex flex-col items-start">
          <span className="transition-all duration-300 font-medium group-hover:text-blue-400">
            {label}
          </span>
          <span className="text-sm">{subLabel}</span>
        </div>
        <div className="transition-all duration-300 transform -translate-x-[10px] opacity-0 group-hover:opacity-100 group-hover:translate-x-0 flex justify-end items-center flex-1">
          <ChevronRight className="text-blue-400 w-5 h-5" />
        </div>
      </div>
    </a>
  );
};

export default function DesktopNav() {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  return (
    <div className="flex items-center justify-end space-x-4">
      {NAV_ITEMS.map((navItem: NavItem) => (
        <div
          key={navItem.label}
          className="hover:transform hover:translate-y-[1px] transition-all duration-[0.1s]"
          onMouseEnter={() => setHoveredItem(navItem.label)}
          onMouseLeave={() => setHoveredItem(null)}
        >
          <div className="relative group">
            <Link
              href={navItem.href ?? "#"}
              className={`p-2 text-md font-semibold no-underline transition-all duration-200 ${
                hoveredItem !== null
                  ? hoveredItem === navItem.label
                    ? "text-[rgba(255,255,255,1)]"
                    : "text-[rgba(255,255,255,0.5)]"
                  : "text-[rgba(255,255,255,0.8)]"
              }`}
              target={navItem.href?.startsWith("http") ? "_blank" : undefined}
              rel={
                navItem.href?.startsWith("http")
                  ? "noopener noreferrer"
                  : undefined
              }
            >
              {navItem.label}
            </Link>

            {navItem.children && (
              <div className="hidden group-hover:block absolute top-full left-0 mt-1 z-[1000]">
                <div className="shadow-xl backdrop-blur-[100px] bg-[rgba(20,20,20,0.9)] border border-[rgba(255,255,255,0.1)] p-4 rounded-xl min-w-sm">
                  <div className="w-full backdrop-blur-[100px]">
                    {navItem.children.map((child) => (
                      <DesktopSubNav key={child.label} {...child} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

interface NavItem {
  label: string;
  href?: string;
  children?: Array<{
    label: string;
    subLabel: string;
    href: string;
  }>;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Pricing",
    href: "/pricing",
  },
  {
    label: "Book Demo",
    href: "https://cal.com/team/speck/demo",
  },
];
