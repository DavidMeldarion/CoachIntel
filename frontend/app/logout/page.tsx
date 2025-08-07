"use client";
import { useEffect } from 'react';
import { signOut } from 'next-auth/react';

export default function LogoutPage() {
  
  useEffect(() => {
    const performLogout = async () => {
      console.log('[LogoutPage] Starting NextAuth logout process');
      
      try {
        // Use NextAuth signOut function
        console.log('[LogoutPage] Calling NextAuth signOut');
        await signOut({
          callbackUrl: '/login',
          redirect: true
        });
      } catch (error) {
        console.error('[LogoutPage] Logout failed:', error);
        // Fallback: redirect to login anyway
        window.location.href = '/login';
      }
    };
    
    performLogout();
  }, []);
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div>Logging out...</div>
    </div>
  );
}
