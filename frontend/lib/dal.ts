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
  console.log('[DAL] verifySession starting...');
  
  // Debug: Log all available cookies
  const allCookies = await cookies();
  const cookieNames = Array.from(allCookies.getAll()).map(c => c.name);
  console.log('[DAL] All available cookies:', cookieNames);
  
  const sessionCookie = allCookies.get('session')?.value;
  const userCookie = allCookies.get('user')?.value;
  console.log('[DAL] session cookie exists?', !!sessionCookie);
  console.log('[DAL] user cookie exists?', !!userCookie);
  console.log('[DAL] session cookie preview:', sessionCookie ? sessionCookie.substring(0, 20) + '...' : 'none');
  
  const session = await decrypt(sessionCookie);
  console.log('[DAL] decrypted session:', session);

  if (!session?.userId) {
    console.log('[DAL] verifySession failed - no userId');
    return null;
  }

  console.log('[DAL] verifySession success - userId:', session.userId, 'email:', session.email);
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
  console.log('[DAL] getUser starting...');
  const session = await verifySession();
  console.log('[DAL] getUser session result:', session);
  
  if (!session) {
    console.log('[DAL] getUser failed - no session');
    return null;
  }

  try {
    console.log('[DAL] making backend call to /me...');
    const allCookies = (await cookies()).toString();
    console.log('[DAL] sending cookies:', allCookies);
    
    const response = await fetch(getApiUrl('/me'), {
      headers: {
        'Cookie': allCookies,
      },
      cache: 'no-store', // Always fetch fresh data
    });

    console.log('[DAL] backend response status:', response.status);
    console.log('[DAL] backend response ok:', response.ok);

    if (!response.ok) {
      console.log(`[DAL] Backend /me call failed with status: ${response.status}`);
      return null;
    }

    const userData = await response.json();
    console.log('[DAL] backend user data:', userData);
    
    const userResult = {
      email: userData.email,
      name: userData.name || `${userData.first_name} ${userData.last_name}`.trim() || "User",
      first_name: userData.first_name,
      last_name: userData.last_name,
      fireflies_api_key: userData.fireflies_api_key,
      zoom_jwt: userData.zoom_jwt,
      phone: userData.phone,
      address: userData.address,
    };
    
    console.log('[DAL] final user result:', userResult);
    return userResult;
  } catch (error) {
    console.error('[DAL] Failed to fetch user from backend:', error);
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
