"use client";
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function LogoutPage() {
  const router = useRouter();
  useEffect(() => {
    // Call API route to clear the cookie server-side
    fetch('/api/logout', { method: 'POST' })
      .then(() => {
        localStorage.clear();
        sessionStorage.clear();
        router.replace('/login');
      });
  }, [router]);
  return null;
}
