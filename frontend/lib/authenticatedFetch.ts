import { getSession } from "next-auth/react";
import { getApiUrl } from "./apiUrl";

// Helper function to make authenticated API calls with NextAuth
export async function authenticatedFetch(
  endpoint: string, 
  options: RequestInit = {}
): Promise<Response> {
  const session = await getSession();
  
  const headers: Record<string, string> = {
    ...options.headers as Record<string, string>,
  };
  
  // Add user email header if session exists
  if (session?.user?.email) {
    headers["x-user-email"] = session.user.email;
  }
  
  console.log(`[authenticatedFetch] Making request to ${endpoint} with email: ${session?.user?.email}`);
  
  return fetch(getApiUrl(endpoint), {
    ...options,
    headers,
    credentials: "include",
  });
}
