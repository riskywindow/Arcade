import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@atlas/shared-types"],
};

export default nextConfig;
