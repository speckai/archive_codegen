"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useMemo } from "react";

const companies = [
  { name: "GitHub", logo: "/icons/github.svg" },
  { name: "GitLab", logo: "/icons/gitlab.svg" },
  { name: "BitBucket", logo: "/icons/bitbucket.svg" },
  { name: "Slack", logo: "/icons/slack.svg" },
  { name: "GitHub Issues", logo: "/icons/github-issues.svg" },
  { name: "Jira", logo: "/icons/jira.svg" },
  { name: "Linear", logo: "/icons/linear.svg" },
  { name: "Asana", logo: "/icons/asana.svg" },
  { name: "Monday", logo: "/icons/monday.svg" },
];

export default function Integrations() {
  const companyPositions = useMemo(() => {
    return companies.map((company, index) => {
      const angle = index * (360 / companies.length) * (Math.PI / 180);
      const radius = 180;
      const x = Math.round(Math.cos(angle) * radius);
      const y = Math.round(Math.sin(angle) * radius);

      return {
        company,
        style: {
          left: "50%",
          top: "50%",
          transform: `translate(-50%, -50%) translate(${x}px, ${y}px)`,
          boxShadow: "0 0 10px rgba(0,0,0,0.2)",
        },
      };
    });
  }, []);

  return (
    <div className="w-full mx-auto py-16 lg:py-24 px-5 sm:px-8 md:px-16 overflow-hidden -mt-40">
      <motion.div
        whileInView={{ y: 0, opacity: 1 }}
        initial={{ y: 50, opacity: 0 }}
        transition={{
          duration: 0.75,
          ease: [0.83, 0, 0.17, 1],
        }}
        viewport={{ once: true }}
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-10 lg:gap-16">
          <div className="flex flex-col space-y-5 md:max-w-md lg:max-w-xl">
            <h2 className="font-bold text-3xl sm:text-4xl md:text-5xl bg-gradient-to-b from-white to-[rgb(200,200,200)] bg-clip-text text-transparent">
              Integrate from end to end.
            </h2>
            <p className="text-gray-300 text-base sm:text-lg">
              Speck integrates with your entire ecosystem, from your bug
              tracking tool to your CI/CD pipeline.
            </p>
          </div>

          <div className="relative w-full md:w-1/2 h-[400px] mt-8 md:mt-0">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(10,39,255,0.1)_0%,rgba(10,39,82,0)_50%)]"></div>

            <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10 w-28 h-28 hover:scale-110 transition-transform duration-200">
              <div className="w-full h-full relative">
                <Image
                  src="/logos/no-bg/speck-logo-512.webp"
                  alt="Speck"
                  width={112}
                  height={112}
                  className="rounded-full bg-[#1A2232] p-2 filter drop-shadow-[0_0_15px_rgba(10,39,255,0.3)]"
                />
              </div>
            </div>

            <motion.div
              className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full h-full"
              animate={{ rotate: 360 }}
              transition={{
                duration: 40,
                ease: "linear",
                repeat: Infinity,
              }}
            >
              {companyPositions.map((item, index) => (
                <div
                  key={index}
                  className="absolute w-12 h-12 bg-[#1A2232] rounded-full flex items-center justify-center hover:scale-105 transition-transform duration-200"
                  style={item.style}
                >
                  <motion.div
                    className="w-6 h-6 relative"
                    animate={{ rotate: -360 }}
                    transition={{
                      duration: 40,
                      ease: "linear",
                      repeat: Infinity,
                    }}
                  >
                    <Image
                      src={item.company.logo}
                      alt={item.company.name}
                      width={24}
                      height={24}
                      className="object-contain"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = "/vercel.svg";
                      }}
                    />
                  </motion.div>
                </div>
              ))}
            </motion.div>

            {/* Decorative dots grid in background */}
            <div className="absolute inset-0 opacity-20 pointer-events-none">
              <div
                className="w-full h-full"
                style={{
                  backgroundImage: "url('/backgrounds/grid.svg')",
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                  maskImage:
                    "radial-gradient(circle at center, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 60%)",
                  WebkitMaskImage:
                    "radial-gradient(circle at center, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 60%)",
                }}
              ></div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
