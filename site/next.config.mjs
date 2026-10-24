/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: ["@once-ui-system/core"],
  },
};

export default nextConfig;
