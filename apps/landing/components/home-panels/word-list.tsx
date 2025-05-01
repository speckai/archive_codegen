"use client";

import { motion } from "framer-motion";

interface MotionTextProps {
  text: string;
  delay: number;
}

const MotionText = ({ text, delay }: MotionTextProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay }}
    viewport={{ once: true }}
  >
    <h2 className="text-xl sm:text-3xl md:text-5xl font-bold text-center leading-tight">
      {text}
    </h2>
  </motion.div>
);

export default function WordList() {
  return (
    <div className="w-full bg-[rgba(7,18,42,0.05)] py-10 z-10 flex justify-center items-center mt-5">
      <div className="max-w-4xl mx-auto text-center">
        <div className="flex flex-wrap justify-center gap-4">
          <MotionText text="Show." delay={0.2} />
          <MotionText text="Describe." delay={0.4} />
          <MotionText text="Ship." delay={0.6} />
        </div>
      </div>
    </div>
  );
}
