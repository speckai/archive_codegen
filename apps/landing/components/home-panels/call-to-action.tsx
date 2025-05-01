"use client";

import { ChevronRight } from "lucide-react";
import Image from "next/image";
import { RadialButton } from "../ui/custom/radial-button";

export default function CallToAction() {
  return (
    <div className="bg-[rgba(50,100,255,0.06)] mx-auto w-[90%] border border-b-0 border-[rgba(255,255,255,0.1)] rounded-t-3xl mt-8 p-4">
      <div className="w-full m-auto p-auto text-center">
        <div className="relative">
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-28 h-28 bg-[rgba(50,100,255,0.4)] blur-[20px] rounded-full" />
          <Image
            src="/logos/no-bg/speck-logo-1024.webp"
            alt="Speck"
            width={112}
            height={112}
            className="mx-auto mb-8 mt-16 relative"
            draggable={false}
          />
        </div>

        <h2 className="text-6xl mb-16 text-center leading-[1.05] bg-clip-text text-transparent bg-gradient-to-b from-[#F7FAFC] via-[#E2E8F0] to-[#808DA0]">
          Report and fix faster.
          <br />
          Available now.
        </h2>

        <div className="mb-10 w-fit mx-auto">
          <RadialButton
            onClick={() => {
              window.open("https://cal.com/team/speck/demo", "_blank");
            }}
            rightIcon={ChevronRight}
            className="border-[rgba(30,80,200,0.6)]"
          >
            Book Demo
          </RadialButton>
        </div>
      </div>
    </div>
  );
}
