/** @type {import('next').NextConfig} */
const nextConfig = {
    experimental: {
        proxyClientMaxBodySize: '100mb',
        serverActions: {
            bodySizeLimit: '100mb',
        },
    },
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://127.0.0.1:8000/api/:path*', // Proxy to Backend
            },
            {
                source: '/audio_jobs/:path*',
                destination: 'http://127.0.0.1:8000/audio_jobs/:path*', // Proxy to Backend Static Files
            },
        ]
    },
};

export default nextConfig;
