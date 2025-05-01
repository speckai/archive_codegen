import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/docs",
        destination: "https://speck.mintlify.dev/docs/introduction",
      },
      {
        source: "/docs/:path*",
        destination: "https://speck.mintlify.dev/docs/:path*",
      },
      {
        source: "/ingest/static/:path*",
        destination: "https://us-assets.i.posthog.com/static/:path*",
      },
      {
        source: "/ingest/:path*",
        destination: "https://us.i.posthog.com/:path*",
      },
      {
        source: "/ingest/decide",
        destination: "https://us.i.posthog.com/decide",
      },
    ];
  },

  images: {
    domains: ["assets.speck.sh"],
  },

  async redirects() {
    return [
      {
        source: "/demo",
        destination: "https://cal.com/team/speck/demo",
        permanent: true,
      },
    ];
  },

  // This is required to support PostHog trailing slash API requests
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
