import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser calls /api on the page's own origin, and these servers forward it to the API.
// That keeps the session cookie first-party, which SameSite=Strict requires (ADR 0004).
const apiTarget = process.env.FINGUARD_API_PROXY_TARGET ?? "http://127.0.0.1:8010";
const proxy = {
  "/api": { target: apiTarget, changeOrigin: false },
  "/health": { target: apiTarget, changeOrigin: false },
};

// Served with the production build by `vite preview`, and checked by the browser tests. The
// development server leaves it off, because hot reloading injects inline code.
export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

export default defineConfig({
  plugins: [react()],
  // 127.0.0.1, not localhost: on Windows localhost may bind IPv6 only, as the API and database
  // address issues showed. The API's allowed origins list both forms.
  server: { host: "127.0.0.1", port: 5173, proxy },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    proxy,
    headers: {
      "Content-Security-Policy": CONTENT_SECURITY_POLICY,
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
    },
  },
});
