import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export so the FastAPI backend can serve the app on one origin
  // (needed to run everything behind a single tunnel).
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
