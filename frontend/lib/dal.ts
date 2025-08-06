import { cache } from 'react';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { decrypt } from './session';
import { getApiUrl } from './apiUrl';

export interface User {
  email: string;
  name: string;
  first_name?: string;
  last_name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
  phone?: string;
  address?: string;
}

// Verify the session and return user data - uses new session cookie only
export const verifySession = cache(async () => {
  const sessionCookie = (await cookies()).get('session')?.value;
  const session = await decrypt(sessionCookie);

  if (!session?.userId) {
    return null;
  }

  return { isAuth: true, userId: session.userId, email: session.email };
});

// Verify session for protected routes - will redirect to login if not authenticated
export const requireAuth = cache(async () => {
  const session = await verifySession();
  
  if (!session) {
    redirect('/login');
  }
  
  return session;
});

// Get current user data - cached during a single request
export const getUser = cache(async (): Promise<User | null> => {
  const session = await verifySession();
  if (!session) return null;

  try {
    const response = await fetch(getApiUrl('/me'), {
      headers: {
        'Cookie': (await cookies()).toString(),
      },
      cache: 'no-store', // Always fetch fresh data
    });

    if (!response.ok) {
      console.log(`Backend /me call failed with status: ${response.status}`);
      return null;
    }

    const userData = await response.json();
    return {
      email: userData.email,
      name: userData.name || `${userData.first_name} ${userData.last_name}`.trim() || "User",
      first_name: userData.first_name,
      last_name: userData.last_name,
      fireflies_api_key: userData.fireflies_api_key,
      zoom_jwt: userData.zoom_jwt,
      phone: userData.phone,
      address: userData.address,
    };
  } catch (error) {
    console.error('Failed to fetch user from backend', error);
    return null;
  }
});

// Check if user has specific permissions/roles
export const canAccessDashboard = cache(async (): Promise<boolean> => {
  const user = await getUser();
  return user !== null;
});

export const canAccessProfile = cache(async (): Promise<boolean> => {
  const user = await getUser();
  return user !== null;
});

// Specific authorization checks
export const requireCompleteProfile = cache(async (): Promise<boolean> => {
  const user = await getUser();
  if (!user) return false;
  
  return !!(user.first_name && user.last_name);
});
