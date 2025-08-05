// Utility function to properly join API base URL with endpoint paths
export function getApiUrl(endpoint: string = ''): string {
  // If we're using Vercel rewrites, use relative paths
  if (process.env.NODE_ENV === 'production' && process.env.VERCEL) {
    // Remove leading slash for relative paths
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;
    return `/api/${cleanEndpoint}`;
  }
  
  // For development or direct Railway access
  const baseUrl = process.env.NEXT_PUBLIC_BROWSER_API_URL || 
                  process.env.NEXT_PUBLIC_API_URL || 
                  "http://localhost:8000";
  
  // Remove trailing slash from base URL
  const cleanBaseUrl = baseUrl.replace(/\/+$/, '');
  
  // Ensure endpoint starts with a slash
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  return `${cleanBaseUrl}${cleanEndpoint}`;
}
