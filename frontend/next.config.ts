import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Minimal, self-contained build output for the Azure Container Apps
  // Docker image (see docs/DEPLOYMENT_AZURE.md) — copies only the files
  // the server actually needs, not the full node_modules tree.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
