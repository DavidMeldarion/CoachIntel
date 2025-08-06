"use client";
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useUser } from '../../lib/userContext';

export default function LogoutPage() {
  const router = useRouter();
  const { refreshUser } = useUser();
  
  useEffect(() => {
    // Call API route to clear the cookie server-side
    fetch('/api/logout', { method: 'POST' })
      .then(async () => {
        await refreshUser(); // Clear user context
        localStorage.clear();
        sessionStorage.clear();
        router.replace('/login');
      })
      .catch(async () => {
        // Even if logout fails, clear local state
        await refreshUser();
        localStorage.clear();
        sessionStorage.clear();
        router.replace('/login');
      });
  }, [router, refreshUser]);
  
  return null;
}
