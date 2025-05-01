"use client";

import { motion } from "framer-motion";
import Image from "next/image";

export default function MainVideo() {
  return (
    <motion.div
      initial={{ scale: 0.5, opacity: 0 }}
      animate={{ scale: 0.9, opacity: 1 }}
      transition={{
        duration: 1,
        delay: 0.5,
        ease: [0.83, 0, 0.17, 1],
      }}
      whileInView={{ scale: 1 }}
    >
      <div className="w-[95%] mx-auto text-center -mt-28 mb-10 rounded-xl">
        <div className="flex justify-center py-[30px]">
          <div className="relative w-full rounded-[10px] border border-white/10 shadow-[0px_20px_30px_rgba(0,0,0,0.5)] overflow-hidden">
            <Image
              src="https://assets.speck.sh/external/landing_main_image.webp"
              alt="Application screenshot"
              width={1920}
              height={1080}
              className="w-full h-auto object-cover"
              priority
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
