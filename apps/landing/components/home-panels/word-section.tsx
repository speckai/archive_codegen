"use client";

import { motion } from "framer-motion";

export default function WordSection() {
  return (
    <div className="bg-[rgba(10,39,82,0.1)] p-10 border-t border-b border-gray-900">
      <div className="max-w-4xl mx-auto flex flex-col justify-center items-center mt-5">
        <motion.div
          whileInView={{ scale: 1 }}
          initial={{ scale: 0.75 }}
          transition={{
            duration: 0.75,
            ease: [0.83, 0, 0.17, 1],
          }}
          viewport={{ once: true }}
        >
          <div className="flex flex-row justify-center items-center text-center">
            <h2 className="text-xl sm:text-3xl md:text-5xl font-light text-center mb-8 leading-tight">
              The first bug tracking platform that <br />
              <div className="font-extrabold text-blue-300">
                fixes your bugs.
              </div>
            </h2>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
