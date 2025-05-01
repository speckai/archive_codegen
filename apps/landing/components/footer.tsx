"use client";

import Image from "next/image";
import Link from "next/link";
import { FaLinkedin, FaYCombinator } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";

interface SocialButtonProps {
  label: string;
  href: string;
  icon: React.ReactElement;
}

const SocialButton = ({ label, href, icon }: SocialButtonProps) => {
  return (
    <Link href={href} target="_blank" rel="noopener noreferrer">
      <button
        aria-label={label}
        className="text-gray-400 hover:text-white bg-transparent p-2 rounded-md text-base sm:text-lg md:text-xl"
      >
        {icon}
      </button>
    </Link>
  );
};

export default function Footer() {
  return (
    <footer className="border-t border-[rgba(255,255,255,0.25)] bg-[rgba(0,0,0,0.1)]">
      <div className="max-w-6xl mx-auto py-2 md:py-4 px-4">
        <div className="flex flex-col sm:flex-row justify-between items-center flex-wrap my-4 md:my-0">
          <div className="flex items-center space-x-2 md:space-x-4 flex-1">
            <Image
              src="/logos/no-bg/speck-logo-512.webp"
              alt="speck"
              width={16}
              height={16}
              className="w-3 h-3 md:w-4 md:h-4"
            />
            <span className="text-gray-300 text-md md:text-sm">
              © 2025 All Rights Reserved
            </span>
          </div>

          <div className="flex space-x-2 md:space-x-6 justify-center text-center relative md:absolute md:left-1/2 md:transform md:-translate-x-1/2 flex-1 mt-4 sm:mt-0">
            <Link
              href="/policies/terms"
              className="text-gray-300 text-sm hover:text-white"
            >
              Terms & Conditions
            </Link>
            <Link
              href="/policies/privacy"
              className="text-gray-300 text-sm hover:text-white"
            >
              Privacy Policy
            </Link>
          </div>

          <div className="flex justify-end sm:flex-1 mt-4 sm:mt-0 space-x-2">
            <SocialButton
              label="Twitter"
              href="https://x.com/speck_ai"
              icon={<FaXTwitter />}
            />
            <SocialButton
              label="LinkedIn"
              href="https://www.linkedin.com/company/speck"
              icon={<FaLinkedin />}
            />
            <SocialButton
              label="Y Combinator"
              href="https://www.ycombinator.com/companies/speck"
              icon={<FaYCombinator />}
            />
          </div>
        </div>
      </div>
    </footer>
  );
}
