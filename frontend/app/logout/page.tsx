"use client";
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function LogoutPage() {
  useEffect(() => {
    // Clear storage immediately
    localStorage.clear();
    sessionStorage.clear();
    
    // Call API route to clear the cookie server-side
    fetch('/api/logout', { method: 'POST' })
      .finally(() => {
        // Always redirect regardless of API success/failure
        window.location.replace('/login');
      });
  }, []);
  
  return (
    <div>Logging out...</div>
  );
}
