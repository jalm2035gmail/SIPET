/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: process.env.FRONTEND_BASE_PATH || "",
  // experimental: {
  //   appDir: false,
  // },
  reactStrictMode: true,
};

module.exports = nextConfig;
