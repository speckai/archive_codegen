"use client";

import { motion } from "framer-motion";
import { createRef, useCallback, useEffect, useMemo, useState } from "react";

interface Section {
  name: string;
  title: string;
  text: string;
  src: string;
  duration: number;
}

const ProcessScrolling = () => {
  const sections: Section[] = useMemo(
    () => [
      {
        name: "capture",
        title: "Capture Recording.",
        text: "Capture a recording of actions, components or screenshots to allow Speck to reproduce your bug. This also captures console logs, device information, file tracing and more.",
        src: "https://speck-site-assets.s3.us-west-1.amazonaws.com/progress/Connect.mp4",
        duration: 4,
      },
      {
        name: "plan",
        title: "Plan with Speck.",
        text: "Based on your recording, Speck creates a bug report and reproduction steps to understand your issue. Work with Speck to tailor this to your liking before it gets turned into an enriched issue.",
        src: "https://speck-site-assets.s3.us-west-1.amazonaws.com/progress/Instruct.mp4",
        duration: 7,
      },
      {
        name: "iterate",
        title: "Iterate Results.",
        text: "After the initial pass to fix the bug, iterate with Speck to get the results you want. Speck produces beautiful results out of the box, but you can iterate to get more specific results.",
        src: "https://speck-site-assets.s3.us-west-1.amazonaws.com/progress/Iterate.mp4",
        duration: 6,
      },
      {
        name: "fix",
        title: "Fix Issue.",
        text: "Speck will use the issue and the reproduction steps to fix and validate the bug, then open a pull request for the issue with your changes. Not only does this fix the bug, but it has more specific context for any further fixes. You can review the changes, and merge them into your repository.",
        src: "https://speck-site-assets.s3.us-west-1.amazonaws.com/progress/Push.mp4",
        duration: 4,
      },
    ],
    [],
  );

  const [activeSection, setActiveSection] = useState<string>("capture");
  const [progress, setProgress] = useState<number>(0);
  const [maxTextHeight, setMaxTextHeight] = useState<number>(0);
  const textRefs = useMemo(
    () => sections.map(() => createRef<HTMLDivElement>()),
    [sections],
  );

  useEffect(() => {
    const currentSection = sections.find((sec) => sec.name === activeSection);
    const interval = setInterval(() => {
      setProgress((prevProgress) => {
        if (prevProgress >= 100) {
          return 0;
        } else {
          return prevProgress + 100 / (currentSection?.duration || 4) / 100;
        }
      });
    }, 10);
    return () => clearInterval(interval);
  }, [activeSection, sections]);

  const nextSection = useCallback(() => {
    setActiveSection((prevSection) => {
      const currentIndex = sections.findIndex(
        (sec) => sec.name === prevSection,
      );
      const nextIndex = (currentIndex + 1) % sections.length;
      return sections[nextIndex].name;
    });
  }, [sections]);

  useEffect(() => {
    if (progress >= 100) {
      nextSection();
    }
  }, [progress, nextSection]);

  const handleButtonClick = (sectionName: string) => {
    setActiveSection(sectionName);
    setProgress(0);
  };

  useEffect(() => {
    const heights = textRefs.map((ref) => ref.current?.offsetHeight ?? 0);
    const maxHeight = Math.max(...heights);
    setMaxTextHeight(maxHeight);
  }, [textRefs]);

  return (
    <div className="w-[99vw] md:w-[99vw] h-[80vh] overflow-y-clip rounded-2xl border border-[rgba(255,255,255,0.1)] bg-gradient-to-b from-[rgba(100,150,255,0.05)] to-transparent">
      <div className="w-[90%] h-[10%] mx-auto py-2">
        <div className="flex items-center justify-between mb-4">
          {sections.map((section, index) => (
            <div key={section.name} className="flex items-center w-1/4">
              <button
                className={`relative overflow-hidden w-full text-[10px] md:text-xs font-${
                  activeSection === section.name ? "700" : "200"
                } ${
                  activeSection === section.name
                    ? "bg-[rgba(39,123,241,0.7)]"
                    : sections.findIndex((sec) => sec.name === activeSection) >
                        index
                      ? "bg-[rgba(39,123,241,0.7)]"
                      : "bg-[rgba(15,60,150,0.2)]"
                } hover:${
                  activeSection === section.name
                    ? "bg-[#2562b8]"
                    : sections.findIndex((sec) => sec.name === activeSection) >
                        index
                      ? "bg-[#1852a3]"
                      : "bg-gray-400"
                } border ${index === 0 ? "rounded-l-md" : ""} ${
                  index === sections.length - 1 ? "rounded-r-md" : ""
                } ${
                  activeSection === section.name
                    ? "border-[rgba(255,255,255,0.2)]"
                    : "border-[rgba(255,255,255,0.1)]"
                } px-3 py-1`}
                onClick={() => handleButtonClick(section.name)}
              >
                <div
                  className="absolute top-0 left-0 h-full bg-[rgba(255,255,255,0.2)] transition-[width] duration-[0.01s] linear"
                  style={{
                    width: `${activeSection === section.name ? progress : 0}%`,
                  }}
                ></div>
                <span className="relative z-10">
                  {section.name.toUpperCase()}
                </span>
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="w-full h-full overflow-x-hidden overflow-y-hidden relative mx-auto">
        <div
          className="flex flex-row h-full transition-all duration-500 ease-in-out"
          style={{
            width: `${sections.length * 100}%`,
            transform: `translateX(-${
              (sections.findIndex((section) => section.name === activeSection) *
                100) /
              sections.length
            }%)`,
          }}
        >
          {sections.map((section, index) => (
            <div
              key={section.name}
              className={`w-[${
                100 / sections.length
              }%] h-full px-2 md:px-5 flex flex-col justify-between mb-4`}
              style={{ width: `${100 / sections.length}%` }}
            >
              <div
                ref={textRefs[index]}
                className="text-[10px] md:text-2xl text-center md:text-left mb-3"
                style={{
                  height: maxTextHeight ? `${maxTextHeight}px` : "auto",
                  transition: "height 0.3s",
                }}
              >
                <strong>{section.title}</strong>
                <span className="hidden md:inline"> </span>
                <br className="md:hidden" />
                {section.text}
              </div>

              <div className="h-auto w-full flex justify-center items-end overflow-x-clip overflow-y-clip aspect-video rounded-lg border border-[rgba(255,255,255,0.3)]">
                <video
                  src={section.src}
                  className="w-full h-full"
                  autoPlay
                  loop
                  muted
                  playsInline
                  style={{ borderRadius: "10px", maxHeight: "900px" }}
                ></video>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default function StepList() {
  return (
    <motion.div
      whileInView={{ opacity: 1, y: 0 }}
      initial={{ opacity: 0, y: 100 }}
      transition={{
        duration: 0.5,
        ease: [0.83, 0, 0.17, 1],
      }}
      viewport={{ once: true, amount: 0.25 }}
    >
      <div className="flex flex-col items-center justify-center mt-5 mb-20">
        <h2 className="mt-5 mb-5 text-3xl text-center px-8">
          Start fixing{" "}
          <span className="text-[rgba(75,150,255,1)] font-bold">
            in minutes, not sprints.
          </span>
        </h2>
        <ProcessScrolling />
      </div>
    </motion.div>
  );
}
