"use client";

import Footer from "@/components/footer";
import CallToAction from "@/components/home-panels/call-to-action";
import Faq from "@/components/home-panels/faq-section";
import HeroSection from "@/components/home-panels/hero-section";
import Integrations from "@/components/home-panels/integrations";
import MainVideo from "@/components/home-panels/main-video";
import PictureSection from "@/components/home-panels/picture-section";
import VideosSection from "@/components/home-panels/videos-section";
import WordSection from "@/components/home-panels/word-section";

export default function Home() {
  return (
    <div className="bg-[radial-gradient(circle_at_50%_-30%,rgba(10,39,255,0.4)_0%,rgba(0,10,15,1)_60%)]">
      <div className="flex flex-col w-full min-h-screen bg-[radial-gradient(circle,rgba(10,39,255,0.1)_0%,rgba(0,10,15,1)_50%)]">
        <HeroSection />
        <MainVideo />
        <WordSection />
        <VideosSection />
        <Integrations />
        <PictureSection />

        <Faq />
        <CallToAction />
        <Footer />
      </div>
    </div>
  );
}
