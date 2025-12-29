/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: "/x402",
  assetPrefix: "/x402",
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}
module.exports = nextConfig;

export default nextConfig