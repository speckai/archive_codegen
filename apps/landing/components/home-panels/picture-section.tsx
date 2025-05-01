"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useState } from "react";

interface PictureCardProps {
  imageSrc: string;
  title: string;
  subtitle: string;
  reverse?: boolean;
}

const PictureCard = ({
  imageSrc,
  title,
  subtitle,
  reverse,
}: PictureCardProps) => {
  const motionProps = {
    whileInView: { opacity: 1, x: 0 },
    initial: { opacity: 0, x: reverse ? -20 : 20 },
    viewport: { once: true, amount: 0.3 },
    transition: { duration: 0.8, ease: [0.83, 0, 0.17, 1] },
  };

  return (
    <motion.div {...motionProps}>
      <div
        className="relative w-full h-full ml-auto mr-0 bg-[rgba(255,255,255,0.05)] p-6 rounded-xl border border-[rgba(255,255,255,0.1)] shadow-2xl"
        style={{
          marginLeft: reverse ? "0" : "auto",
          marginRight: reverse ? "auto" : "0",
        }}
      >
        <div className="mb-6">
          <h3 className="text-4xl font-bold mb-3">{title}</h3>
          <p className="text-xl mb-3 text-[rgba(255,255,255,0.7)]">
            {subtitle}
          </p>
        </div>

        <div className="relative w-full aspect-[2/1] rounded-md shadow-lg overflow-hidden">
          <Image
            src={imageSrc}
            alt={title}
            fill
            className="object-cover object-left-top"
          />
        </div>
      </div>
    </motion.div>
  );
};

const MobilePictureCard = ({ imageSrc, title, subtitle }: PictureCardProps) => {
  const motionProps = {
    whileInView: { opacity: 1, y: 0 },
    initial: { opacity: 0, y: 20 },
    viewport: { once: true, amount: 0.1 },
    transition: { duration: 0.8, ease: [0.83, 0, 0.17, 1] },
  };

  return (
    <div className="bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] shadow-2xl p-4 rounded-xl mb-10">
      <motion.div {...motionProps}>
        <h3 className="text-2xl font-semibold text-center mb-3">{title}</h3>
      </motion.div>
      <motion.div
        {...motionProps}
        transition={{ ...motionProps.transition, delay: 0.2 }}
      >
        <p className="text-md text-[rgba(255,255,255,0.7)] text-center mb-3">
          {subtitle}
        </p>
      </motion.div>
      <motion.div
        {...motionProps}
        transition={{ ...motionProps.transition, delay: 0.4 }}
      >
        <div className="relative w-full aspect-[2/1] rounded-md shadow-2xl overflow-hidden">
          <Image src={imageSrc} alt={title} fill className="object-cover" />
        </div>
      </motion.div>
    </div>
  );
};

export default function PictureSection() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);

    return () => {
      window.removeEventListener("resize", checkMobile);
    };
  }, []);

  const Card = isMobile ? MobilePictureCard : PictureCard;

  const cards = [
    {
      imageSrc: "/screenshots/side-section/background.png",
      title: "Speck works in the background",
      subtitle:
        "Don't wait around while your bug is being fixed, Speck runs in an isolated sandbox with it's own shell, file system and web browser.",
      reverse: false,
    },
    {
      imageSrc: "/screenshots/side-section/report.png",
      title: "Report anywhere and fix immediately",
      subtitle:
        "Product Managers, Quality Assurance Engineers and Customer Success Managers all use Speck to report bugs quickly and deploy a fix within minutes.",
      reverse: true,
    },
    {
      imageSrc: "/screenshots/side-section/seamless.png",
      title: "Seamless Integration",
      subtitle:
        "Speck makes sure that any edits adhere to the code and design standards of your website. Speck also syncs with your GitHub and creates pull requests for you to review.",
      reverse: false,
    },
  ];

  const leftColumnCards = cards.filter((_, i) => i % 2 !== 0);
  const rightColumnCards = cards.filter((_, i) => i % 2 === 0);

  return (
    <div className="w-full py-10 px-5 md:px-20 overflow-hidden h-auto">
      {isMobile ? (
        cards.map((card, i) => <Card key={i} {...card} />)
      ) : (
        <div className="flex flex-row gap-6 min-h-full items-stretch">
          <div className="flex-1 flex flex-col justify-center self-stretch">
            {leftColumnCards.map((card, i) => (
              <div key={i} className="w-full mb-6">
                <Card {...card} />
              </div>
            ))}
          </div>

          <div className="flex-1 flex flex-col self-stretch">
            {rightColumnCards.map((card, i) => (
              <div
                key={i}
                className={`w-full ${i < rightColumnCards.length - 1 ? "mb-6" : ""}`}
              >
                <Card {...card} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
