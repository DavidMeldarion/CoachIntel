// Utility function to properly join API base URL with endpoint paths
export function getApiUrl(endpoint: string = ''): string {
  // Check if we have a direct API URL configured (Railway deployment)
  const directApiUrl = process.env.NEXT_PUBLIC_API_URL;
  
  // If we have a direct API URL, use it (Railway approach)
  if (directApiUrl) {
    // Remove trailing slash from base URL
    let cleanBaseUrl = directApiUrl.replace(/\/+$/, '');
    
    // Force HTTPS in production to prevent mixed content errors
    if (process.env.NODE_ENV === 'production' && cleanBaseUrl.startsWith('http://')) {
      cleanBaseUrl = cleanBaseUrl.replace('http://', 'https://');
    }
    
    // Ensure endpoint starts with exactly one slash
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    
    return `${cleanBaseUrl}${cleanEndpoint}`;
  }
  
  // Fallback to Vercel rewrites approach if no direct API URL
  if (process.env.NODE_ENV === 'production' && process.env.VERCEL) {
    // Remove leading slash for relative paths and ensure proper concatenation
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;
    return `/api/${cleanEndpoint}`;
  }
  
  // Development fallback
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `http://localhost:8000${cleanEndpoint}`;
}
