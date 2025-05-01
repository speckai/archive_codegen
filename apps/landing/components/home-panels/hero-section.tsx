"use client";

import { motion } from "framer-motion";
import { FaPhone } from "react-icons/fa6";
import { RadialButton } from "../ui/custom/radial-button";
import Backers from "./backers";

export default function HeroSection() {
  const sentence = "Report and fix bugs with AI.";
  const words = sentence.split(" ");

  return (
    <div className="w-full max-w-6xl mx-auto min-h-[50vh] bg-[radial-gradient(circle_at_50%_-30%,rgba(10,39,255,0.35)_0%,rgba(10,39,82,0)_50%)]">
      <motion.div
        whileInView={{ y: 0, opacity: 1 }}
        initial={{ y: 100, opacity: 0 }}
        transition={{
          duration: 0.75,
          ease: [0.83, 0, 0.17, 1],
        }}
        viewport={{ once: true }}
      >
        <div className="flex flex-col items-center space-y-8 md:space-y-10 mt-28 mb-32 px-5 sm:px-8 md:px-16">
          <Backers />

          <h1 className="flex flex-wrap justify-center w-full">
            {words.map((word, index) => (
              <motion.span
                key={index}
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.3, delay: index * 0.15 + 0.3 }}
                style={{ display: "inline-block", marginRight: "0.7em" }}
              >
                <span className="font-bold text-5xl sm:text-5xl md:text-6xl bg-gradient-to-b from-white to-[rgb(200,200,200)] bg-clip-text text-transparent text-center pb-[0.1em] mt-[-16px] mb-[-0.1em] leading-[105%] max-w-4xl filter drop-shadow-[0_0_10px_rgba(0,100,255,0.5)]">
                  {word}
                </span>
              </motion.span>
            ))}
          </h1>

          <h2 className="text-gray-300 text-center text-base sm:text-lg md:text-xl mt-[-8px] max-w-3xl">
            Capture and reproduce bugs with Speck to get automated fixes.
            <br />
            Keep your customers happy by resolving issues in record time.
          </h2>

          <div className="flex flex-row items-center justify-center gap-6">
            <RadialButton
              onClick={() => {
                window.open("https://cal.com/team/speck/demo", "_blank");
              }}
              leftIcon={FaPhone}
              leftIconNotAnimated={true}
              leftIconProps={{
                className: "h-2 w-4",
              }}
              className="py-5 text-md"
            >
              Book Demo
            </RadialButton>
            <RadialButton
              onClick={() => {
                window.open("https://app.speck.sh", "_blank");
              }}
              bg={["rgba(255, 255, 255, 0.1)", "rgba(255, 255, 255, 0.05)"]}
              border="1px solid rgba(255, 255, 255, 0.05)"
              isPulseDisabled={true}
              className="py-5 pl-5 pr-3"
              boxShadow="none"
            >
              Get Started
            </RadialButton>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
