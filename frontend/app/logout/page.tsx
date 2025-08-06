"use client";
import { useEffect } from 'react';
import { logout } from '../../lib/auth-actions';

export default function LogoutPage() {
  
  useEffect(() => {
    const performLogout = async () => {
      console.log('[LogoutPage] Starting logout process');
      
      try {
        // Use Server Action logout function
        console.log('[LogoutPage] Calling Server Action logout');
        await logout();
      } catch (error) {
        console.error('[LogoutPage] Logout failed:', error);
        // Fallback: clear storage and redirect anyway
        localStorage.clear();
        sessionStorage.clear();
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
