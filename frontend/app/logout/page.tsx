"use client";
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useUser } from '../../lib/userContext';

export default function LogoutPage() {
  const router = useRouter();
  const { logout } = useUser();
  
  useEffect(() => {
    const performLogout = async () => {
      console.log('[LogoutPage] Starting logout process');
      
      try {
        // Use the userContext logout function
        console.log('[LogoutPage] Calling userContext logout');
        await logout();
        
        console.log('[LogoutPage] Redirecting to login');
        router.replace('/login');
      } catch (error) {
        console.error('[LogoutPage] Logout failed:', error);
        // Fallback: clear storage and redirect anyway
        localStorage.clear();
        sessionStorage.clear();
        router.replace('/login');
      }
    };
    
    performLogout();
  }, [router, logout]);
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div>Logging out...</div>
    </div>
  );
}
