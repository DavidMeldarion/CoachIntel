/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Add basePath for Vercel monorepo deployment
  basePath: process.env.NODE_ENV === 'production' ? '/frontend' : '',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_BROWSER_API_URL: process.env.NEXT_PUBLIC_BROWSER_API_URL,
  },
};

module.exports = nextConfig;
