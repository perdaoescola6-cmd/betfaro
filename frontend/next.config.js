/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['localhost', 'betfaro.com.br'],
  },
  // Disable static page generation to prevent build errors when env vars are not available
  output: 'standalone',
}

module.exports = nextConfig
