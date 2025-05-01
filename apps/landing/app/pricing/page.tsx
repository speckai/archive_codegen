"use client";

import { RadialButton } from "@/components/ui/custom/radial-button";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import React, { useEffect } from "react";
import { toast } from "sonner";

interface PricingPlanProps {
  index: number;
  title: string;
  price: number | string;
  per: string | null;
  perSeat?: boolean;
  features: string[];
  buttonText: string;
  buttonVariant: "solid" | "outline";
  url?: string;
  onClick?: () => void;
}

const PricingPlan: React.FC<PricingPlanProps> = ({
  index,
  title,
  price,
  per,
  perSeat = false,
  features,
  buttonText,
  buttonVariant,
  url,
  onClick,
}) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
    if (url) {
      window.open(url, "_blank");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.75,
        delay: index * 0.25 + 0.5,
        ease: "easeInOut",
      }}
      className="w-full md:w-[28vw]"
    >
      <div className="mb-4 rounded-xl overflow-hidden border border-[rgba(255,255,255,0.3)] shadow-md">
        {/* Header Section */}
        <div className="py-4 px-12 text-center">
          <h3 className="font-medium text-2xl">{title}</h3>
          <div className="flex items-center justify-center">
            <span className="text-3xl font-semibold">
              {typeof price === "number" ? "$" : ""}
            </span>
            <span className="text-5xl font-bold">{price}</span>
            <span className="text-3xl text-gray-500">
              {per ? `/${per}` : ""}
            </span>
          </div>
          {perSeat && (
            <div className="text-gray-400 text-md mt-1">per seat</div>
          )}
        </div>

        {/* Features Section */}
        <div className="p-4 bg-gradient-to-t from-[rgba(10,40,80,0.4)] to-transparent rounded-b-xl">
          <ul className="space-y-3 px-12 mb-8">
            {features.map((feature, idx) => (
              <li key={idx} className="flex items-start">
                {feature[0] !== "!" ? (
                  <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                ) : null}
                <span>{feature[0] !== "!" ? feature : feature.slice(1)}</span>
              </li>
            ))}
          </ul>
          <div className="w-[80%] mx-auto pt-7">
            <RadialButton
              className="w-full"
              isOutlined={buttonVariant === "outline"}
              onClick={handleClick}
              isPulseDisabled
              boxShadow="0px 0px 20px 0px rgba(30, 80, 200, 1)"
            >
              {buttonText}
            </RadialButton>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default function Pricing() {
  const handleCopyClick = () => {
    navigator.clipboard.writeText("support@speck.sh");
    toast("Email copied to clipboard", {
      description: "support@speck.sh",
    });
  };

  useEffect(() => {
    document.title = "Pricing | Speck";
  }, []);

  return (
    <div className="bg-[radial-gradient(circle_at_50%_-30%,rgba(10,39,255,0.4)_0%,rgba(0,10,15,1)_60%)] w-full min-h-screen py-24">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 1.5,
          ease: [0, 0.71, 0.2, 0.8],
        }}
        className="text-center mb-4"
      >
        <h1 className="text-5xl font-bold mb-2">Pricing</h1>
        <p className="text-xl text-gray-300 max-w-xl mx-auto">
          Get access to Speck. Choose the plan that&apos;s right for your team.
        </p>
      </motion.div>

      <div className="flex flex-col md:flex-row justify-center items-center gap-10 py-10 px-4 md:px-0">
        <PricingPlan
          index={0}
          title="Team"
          price={80}
          per="month"
          perSeat={true}
          features={[
            "Access to Speck",
            "Unlimited tasks",
            "Unlimited codebases",
            "White-glove onboarding",
          ]}
          buttonText="Get Started"
          buttonVariant="solid"
          url="https://buy.stripe.com/6oEcQzaDUeLubcseV3"
        />
        <PricingPlan
          index={1}
          title="Enterprise"
          price="Custom"
          per={null}
          features={[
            "Everything in Starter",
            "Deploy to your own VPC",
            "Priority 1:1 Support",
            "Dedicated support engineer",
          ]}
          buttonText="Contact Us"
          buttonVariant="outline"
          onClick={handleCopyClick}
        />
      </div>
    </div>
  );
}
