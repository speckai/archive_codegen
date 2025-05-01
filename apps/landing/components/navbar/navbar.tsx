"use client";

import { Menu, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import ButtonStack from "./button-stack";
import DesktopNav from "./desktop-nav";
import MobileNav from "./mobile-nav";

const Logo = () => {
  return (
    <div className="flex items-center">
      <Link href="/" className="hover:no-underline">
        <Image
          src="/logos/no-bg/speck-logo-512.webp"
          alt="speck"
          width={24}
          height={24}
          className="mr-5 opacity-90"
        />
      </Link>
    </div>
  );
};

function useDisclosure() {
  const [isOpen, setIsOpen] = useState(false);
  const onToggle = () => setIsOpen(!isOpen);
  return { isOpen, onToggle };
}

export default function Navbar() {
  const { isOpen, onToggle } = useDisclosure();
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
    <div className="fixed top-0 left-0 right-0 z-50">
      <div
        className="transition-[height] duration-[0.4s] ease-[cubic-bezier(0.32,0.04,0.15,0.97)]"
        style={{ height: shouldMinimize ? "10px" : "0px" }}
      />

      <div
        className={`
          text-white
          bg-[rgba(4,19,85,0.2)]
          py-2 px-4
          border-solid
          transition-all duration-[0.4s] ease-[cubic-bezier(0.32,0.04,0.15,0.97)]
          backdrop-blur-[30px]
          border-[rgba(82,135,195,0.25)]
          ${
            shouldMinimize
              ? "w-[50%] sm:w-[50%] md:w-[36rem] lg:w-[64rem] border rounded-xl"
              : "w-full border-b"
          }
          mx-auto
        `}
      >
        <div
          className={`
            flex items-center justify-between mx-auto
            transition-[width] duration-[0.4s] ease-[cubic-bezier(0.32,0.04,0.15,0.97)]
            max-w-5xl
            ${shouldMinimize ? "w-full" : "w-full"}
          `}
        >
          <Logo />

          <div className="flex mx-[-0.5rem] flex-[1_1_auto] justify-start items-center">
            <Link href="/" className="hover:no-underline">
              <div className="flex">
                <span
                  className="
                    font-bold text-lg 
                    transition-[opacity_0.5s_cubic-bezier(0.32,0.04,0.15,0.97),transform_0.75s_cubic-bezier(0.32,0.04,0.15,0.97),font-size_0.75s_cubic-bezier(0.32,0.04,0.15,0.97)]
                  "
                >
                  Speck
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            <div className="w-full hidden md:block">
              <DesktopNav />
            </div>

            <ButtonStack />

            <div className="flex md:hidden ml-[-0.5rem]">
              <button
                onClick={onToggle}
                className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700/10"
                aria-label="Toggle Navigation"
              >
                {isOpen ? (
                  <X className="w-5 h-5" />
                ) : (
                  <Menu className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div
        className={`
          transition-all duration-300 ease-in-out
          backdrop-blur-[10px]
          ${isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0 overflow-hidden px-12"}
          ${shouldMinimize ? "w-[80%] mx-auto" : "w-full mx-auto"}
        `}
      >
        {isOpen && <MobileNav />}
      </div>
    </div>
  );
}
