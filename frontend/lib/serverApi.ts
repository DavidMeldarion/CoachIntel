// Unified server-to-server API base resolver for Next.js server code (API routes, callbacks)
// Priority:
// 1. INTERNAL_API_URL (docker-compose internal hostname)
// 2. API_URL (explicit backend base URL)
// 3. NEXT_PUBLIC_BROWSER_API_URL or NEXT_PUBLIC_API_URL (public backend base used by browser)
// 4. Default to docker internal hostname in dev
export function getServerApiBase(): string {
  const fromEnv =
    process.env.INTERNAL_API_URL ||
    process.env.API_URL ||
    process.env.NEXT_PUBLIC_BROWSER_API_URL ||
    process.env.NEXT_PUBLIC_API_URL;

  if (fromEnv) return fromEnv.replace(/\/+$/, "");

  // Fallback for local docker-compose dev
  return "http://coachintel-backend:8000";
}
