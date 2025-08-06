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
    // For now, return user data from session - later we can enhance this
    // by calling backend when needed, but for basic navbar functionality this works
    return {
      email: session.email,
      name: session.email.split('@')[0], // Use email prefix as default name
      first_name: '',
      last_name: '',
      fireflies_api_key: '',
      zoom_jwt: '',
      phone: '',
      address: '',
    };
  } catch (error) {
    console.error('Failed to get user data', error);
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
