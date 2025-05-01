"use client";

import { easeOut, motion } from "framer-motion";
import {
  Camera,
  ChartBar,
  Info,
  Network,
  PlaySquare,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { createContext, useEffect, useRef, useState } from "react";

interface Section {
  topic: string;
  title: string;
  text: string;
  src: string;
  icon: React.ReactNode;
  alignment?: "left" | "center" | "right"; // Default is center if not specified
}

interface VideoSectionItemProps {
  section: Section;
  index: number;
  activeIndex: number;
  setActiveIndex: (index: number) => void;
}

const ActiveVideoContext = createContext<{
  activeIndex: number;
  setActiveIndex: (index: number) => void;
}>({
  activeIndex: -1,
  setActiveIndex: () => {},
});

function FeatureButton({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center px-2 py-3 hover:opacity-80 transition-opacity">
      <div className="h-10 w-10 flex items-center justify-center rounded-full bg-gray-800/80 text-blue-400 mb-2">
        {icon}
      </div>
      <span className="text-gray-300 text-xs font-medium text-center">
        {label}
      </span>
    </div>
  );
}

export default function VideosSection() {
  const [activeIndex, setActiveIndex] = useState(-1);

  const sections: Section[] = [
    {
      topic: "Recording",
      title: "Reproduce your bug",
      text: "Click record and Speck will capture your actions and more, including:",
      src: "https://assets.speck.sh/external/demo_recording_button_click.webm",
      alignment: "center",
      icon: (
        <Camera
          size={16}
          className="text-blue-400 drop-shadow-[0_0_10px_rgba(59,130,246,0.9)] filter blur-[0.2px]"
        />
      ),
    },
    {
      topic: "Reporting",
      title: "Generate a bug report",
      text: "Based on your recording, Speck creates a bug report with screenshots, videos, and other assets",
      src: "https://assets.speck.sh/external/demo_bug_report_generation_longer.webm",
      alignment: "left",
      icon: (
        <ChartBar
          size={16}
          className="text-blue-400 drop-shadow-[0_0_10px_rgba(59,130,246,0.9)] filter blur-[0.2px]"
        />
      ),
    },
    {
      topic: "Fix",
      title: "Fixes the bug",
      text: "Speck will give you a before and after screenshot after it attempts a fix on a PR",
      src: "https://assets.speck.sh/external/demo_view_pr.webm",
      alignment: "left",
      icon: (
        <RefreshCw
          size={16}
          className="text-blue-400 drop-shadow-[0_0_10px_rgba(59,130,246,0.9)] filter blur-[0.2px]"
        />
      ),
    },
  ];

  return (
    <ActiveVideoContext.Provider value={{ activeIndex, setActiveIndex }}>
      <div className="mx-auto py-24 px-6 sm:px-8 lg:px-10 relative">
        {sections.map((section, index) => (
          <VideoSectionItem
            key={section.title}
            section={section}
            index={index}
            activeIndex={activeIndex}
            setActiveIndex={setActiveIndex}
          />
        ))}
      </div>
    </ActiveVideoContext.Provider>
  );
}

function VideoSectionItem({
  section,
  index,
  activeIndex,
  setActiveIndex,
}: VideoSectionItemProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const sectionRef = useRef<HTMLDivElement>(null);
  const replayTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isInView = activeIndex === index;
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };

    checkIfMobile();
    window.addEventListener("resize", checkIfMobile);

    return () => {
      window.removeEventListener("resize", checkIfMobile);
    };
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          const calculateCenterDistance = () => {
            const elements = document.querySelectorAll(".video-section-item");
            let closestIndex = -1;
            let closestDistance = Infinity;

            elements.forEach((element, idx) => {
              const rect = element.getBoundingClientRect();
              const viewportHeight = window.innerHeight;
              const elementCenter = rect.top + rect.height / 2;
              const viewportCenter = viewportHeight / 2;
              const distance = Math.abs(elementCenter - viewportCenter);

              if (distance < closestDistance) {
                closestDistance = distance;
                closestIndex = idx;
              }
            });

            if (closestIndex !== -1) {
              setActiveIndex(closestIndex);
            }
          };

          calculateCenterDistance();
          window.addEventListener("scroll", calculateCenterDistance);

          return () => {
            window.removeEventListener("scroll", calculateCenterDistance);
          };
        }
      },
      { threshold: 0.1 },
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => {
      if (sectionRef.current) {
        observer.unobserve(sectionRef.current);
      }
    };
  }, [setActiveIndex]);

  const setupReplayTimer = () => {
    if (replayTimerRef.current) {
      clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }

    if (isInView && videoRef.current) {
      replayTimerRef.current = setTimeout(() => {
        if (videoRef.current && videoRef.current.paused && isInView) {
          videoRef.current
            .play()
            .catch((e) => console.error("Video replay error:", e));
        }
      }, 3000);
    }
  };

  useEffect(() => {
    if (isInView) {
      if (videoRef.current && videoRef.current.paused) {
        videoRef.current
          .play()
          .catch((e) => console.error("Video play error:", e));
      }
    } else {
      if (videoRef.current && !videoRef.current.paused) {
        videoRef.current.pause();
      }
    }

    return () => {
      if (replayTimerRef.current) {
        clearTimeout(replayTimerRef.current);
        replayTimerRef.current = null;
      }
    };
  }, [isInView]);

  useEffect(() => {
    const video = videoRef.current;

    const handlePause = () => {
      if (isInView) {
        setupReplayTimer();
      }
    };

    const handleEnded = () => {
      if (isInView) {
        setupReplayTimer();
      }
    };

    if (video) {
      video.addEventListener("pause", handlePause);
      video.addEventListener("ended", handleEnded);
    }

    return () => {
      if (video) {
        video.removeEventListener("pause", handlePause);
        video.removeEventListener("ended", handleEnded);
      }

      if (replayTimerRef.current) {
        clearTimeout(replayTimerRef.current);
        replayTimerRef.current = null;
      }
    };
  }, [isInView]);

  const isEven = index % 2 === 0;

  const renderFeatureButtons = () => {
    if (section.topic === "Recording") {
      return (
        <div className="mt-2 mb-6">
          <div className="grid grid-cols-3 md:grid-cols-6 gap-x-2 gap-y-4">
            <FeatureButton
              icon={
                <Info
                  size={18}
                  className="text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.7)]"
                />
              }
              label="Device + browser"
            />
            <FeatureButton
              icon={
                <Terminal
                  size={18}
                  className="text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.7)]"
                />
              }
              label="Console logs"
            />
            <FeatureButton
              icon={
                <Network
                  size={18}
                  className="text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.7)]"
                />
              }
              label="Network logs"
            />
            <FeatureButton
              icon={
                <PlaySquare
                  size={18}
                  className="text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.7)]"
                />
              }
              label="Repro steps"
            />
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      ref={sectionRef}
      className="flex flex-col items-center gap-12 mb-16 video-section-item mx-auto"
      initial={{ maxWidth: "90%" }}
      animate={isInView ? { maxWidth: "98%" } : { maxWidth: "90%" }}
      transition={{ duration: 0.4, ease: easeOut }}
    >
      <div
        className={`flex flex-col ${isEven ? "lg:flex-row" : "lg:flex-row-reverse"} w-full items-center gap-16`}
      >
        <motion.div
          className="w-full order-2 lg:order-none sm:w-[45%] md:w-[42%] lg:w-[40%] xl:w-[38%]"
          animate={
            isInView
              ? {
                  flex: "1 0 auto",
                  width: isMobile ? "90%" : "45%",
                }
              : {
                  flex: "0 0 auto",
                  width: isMobile ? "80%" : "38%",
                }
          }
          transition={{ duration: 0.4, ease: easeOut }}
        >
          <div className="rounded-lg overflow-hidden shadow-2xl drop-shadow-[0_20px_50px_rgba(0,0,0,1)] transition-all duration-500">
            <video
              ref={videoRef}
              src={section.src}
              autoPlay={false}
              muted
              playsInline
              className={`w-full h-full object-cover ${isInView ? "opacity-100" : "opacity-70"}`}
              style={{
                minHeight: "320px",
                objectPosition: section.alignment || "center",
                filter:
                  !isInView && !isMobile
                    ? "grayscale(1) brightness(0.8)"
                    : "brightness(1.1)",
                transition: "filter 0.4s ease, opacity 0.4s ease",
              }}
            />
          </div>
        </motion.div>

        <div
          className="w-full order-1 lg:order-none sm:w-[50%] md:w-[52%] lg:w-[55%] mb-8 lg:mb-0"
          style={{
            flex: "0 0 auto",
            width: isMobile ? "100%" : "50%",
          }}
        >
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 flex items-center justify-center">
              {section.icon}
            </div>
            <span className="ml-3 text-sm font-semibold uppercase tracking-wider text-gray-300">
              {section.topic}
            </span>
          </div>
          <motion.h2
            className="text-4xl font-bold mb-6"
            animate={isInView ? { color: "#F9FAFB" } : { color: "#1F2937" }}
            transition={{ duration: 0.4, ease: easeOut }}
          >
            {section.title}
          </motion.h2>
          <motion.p
            className="text-xl mb-8 leading-relaxed"
            animate={isInView ? { color: "#D1D5DB" } : { color: "#4B5563" }}
            transition={{ duration: 0.4, ease: easeOut }}
          >
            {section.text}
          </motion.p>
          {renderFeatureButtons()}
        </div>
      </div>
    </motion.div>
  );
}
