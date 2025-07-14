"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

async function fetchSession() {
  try {
    const res = await fetch("/api/session");
    if (!res.ok) return false;
    const data = await res.json();
    return data.loggedIn;
  } catch {
    return false;
  }
}

export default function Navbar() {
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => {
    async function checkLogin() {
      setLoggedIn(await fetchSession());
    }
    checkLogin();
    // Listen for focus, storage, and navigation events
    window.addEventListener('focus', checkLogin);
    window.addEventListener('storage', checkLogin);
    window.addEventListener('popstate', checkLogin);
    // Listen for cookie changes (logout sets cookie to expire)
    const interval = setInterval(checkLogin, 1000);
    return () => {
      window.removeEventListener('focus', checkLogin);
      window.removeEventListener('storage', checkLogin);
      window.removeEventListener('popstate', checkLogin);
      clearInterval(interval);
    };
  }, []);
  return (
    <nav className="w-full flex items-center justify-between px-8 py-4 bg-white shadow mb-8">
      <div className="flex items-center gap-8">
        <Link href="/dashboard" className="text-xl font-bold text-blue-700 tracking-tight hover:text-blue-900 transition">CoachSync</Link>
        <Link href="/dashboard" className="text-gray-700 font-medium hover:text-blue-700 transition">Dashboard</Link>
        <Link href="/upload" className="text-gray-700 font-medium hover:text-blue-700 transition">Upload</Link>
        <Link href="/timeline" className="text-gray-700 font-medium hover:text-blue-700 transition">Timeline</Link>
      </div>
      {loggedIn ? (
        <Link href="/logout" className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 font-semibold transition">Logout</Link>
      ) : (
        <Link href="/login" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold transition">Login</Link>
      )}
    </nav>
  );
}
