import { Analytics } from "@vercel/analytics/react";
import { Metadata } from "next";
import React from "react";
import { Providers } from "./providers";

interface RootLayoutProps {
  children: React.ReactNode;
}

export const metadata: Metadata = {
  metadataBase: new URL("https://app.speck.sh"),
  description: "AI Bug Resolution Platform",
  keywords: [
    "ai frontend engineer",
    "ai web developer",
    "ai swe",
    "ai bug resolution",
    "bug resolution",
    "bug reporting",
    "bug tracking",
    "web dev",
    "frontend",
    "ai",
    "llm",
    "speck",
    "speck",
    "speck developer",
    "speck ai developer",
  ],
  openGraph: {
    title: "Speck",
    description: "AI Bug Resolution Platform",
    url: "https://app.speck.sh",
    siteName: "Speck",
    images: [
      {
        url: "https://speck.sh/banners/web-banner.jpg",
        width: 1200,
        height: 630,
        alt: "Speck",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Speck",
    description: "AI Bug Resolution Platform",
    siteId: "1467726470533754880",
    images: ["https://speck.sh/banners/web-banner.jpg"],
    creator: "@speck_ai",
  },
  robots: {
    index: true,
    follow: true,
    nocache: true,
    googleBot: {
      index: true,
      follow: true,
      noimageindex: false,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" data-theme="dark">
      <Analytics />
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
