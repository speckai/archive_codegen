import Navbar from "@/components/navbar/navbar";
import { Analytics } from "@vercel/analytics/react";
import type { Metadata } from "next";
import { Figtree } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";
import { PostHogProvider } from "./providers";

const figtree = Figtree({
  subsets: ["latin"],
  display: "swap",
  weight: ["300", "400"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://speck.sh"),
  title: {
    template: "%s | Speck",
    default: "Home | Speck",
  },
  description: "AI Frontend Engineer.",
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
    "speck developer",
    "speck ai developer",
  ],
  openGraph: {
    title: "Speck",
    description: "AI Bug Resolution Platform.",
    url: "https://speck.sh",
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
    description: "AI Bug Resolution Platform.",
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${figtree.className}`}>
      <body className="font-sans font-light">
        <PostHogProvider>
          <Navbar />
          <Analytics />
          {children}
          <Toaster />
        </PostHogProvider>
      </body>
    </html>
  );
}
