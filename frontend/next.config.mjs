/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用严格模式以捕获潜在问题
  reactStrictMode: true,
  
  // 配置后端 API 代理（开发环境）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.BACKEND_URL 
          ? `${process.env.BACKEND_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
