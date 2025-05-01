"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { PiRocketLaunch } from "react-icons/pi";

export default function Backers() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="flex flex-col items-center justify-center mb-6"
    >
      <Link
        href="https://www.ycombinator.com/companies/speck"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="flex items-center bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] px-4 py-1.5 pr-2 rounded-full transition-all duration-200">
          <div className="text-gray-200 text-sm flex items-center mr-2">
            Backed by
          </div>
          <Image
            src="/companies/yc.svg"
            alt="Y Combinator"
            width={80}
            height={30}
            className="object-contain"
          />
          <motion.div
            initial={{ x: -20, scale: 0 }}
            animate={{
              x: isHovered ? 0 : -20,
              scale: isHovered ? 1 : 0,
              width: isHovered ? "20px" : "0px",
              rotate: isHovered ? [0, -9, 6, -5, 9, -6, 5, -4, 3, 0] : 0,
            }}
            transition={{
              duration: 0.2,
              rotate: {
                repeat: Infinity,
                duration: 0.7,
                ease: "linear",
              },
            }}
            className="ml-1"
          >
            <PiRocketLaunch size={13} />
          </motion.div>
        </div>
      </Link>
    </motion.div>
  );
}
