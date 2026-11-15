/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Video files are served by the FastAPI backend, not Next.js.
  // No image optimisation config needed; covers use <video> with backend URLs.
  //
  // Single-URL mode (free tunnel / Docker Compose test): when
  // NEXT_REWRITE_TO_BACKEND=1, /api/* is proxied to the FastAPI backend so
  // one public HTTPS URL serves both frontend and backend, with no CORS
  // issue at all. The backend URL comes from BACKEND_INTERNAL_URL
  // (default http://127.0.0.1:8000). Build the frontend with
  // NEXT_PUBLIC_API_URL=relative in this mode.
  // On Vercel, leave NEXT_REWRITE_TO_BACKEND unset and set
  // NEXT_PUBLIC_API_URL to the Render backend URL instead.
  async rewrites() {
    if (process.env.NEXT_REWRITE_TO_BACKEND !== "1") return [];
    const backend =
      process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
module.exports = nextConfig;
