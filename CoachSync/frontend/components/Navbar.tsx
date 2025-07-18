"use client";
import Link from "next/link";
import { useEffect, useState, useRef } from "react";

interface User {
  email: string;
  first_name?: string;
  last_name?: string;
  name: string | null; // Keep for backward compatibility
}

interface SessionData {
  loggedIn: boolean;
  user?: User;
}

async function fetchSession(): Promise<SessionData> {
  try {
    const res = await fetch("/api/session");
    if (!res.ok) return { loggedIn: false };
    const data = await res.json();
    return data;
  } catch {
    return { loggedIn: false };
  }
}

export default function Navbar() {
  const [sessionData, setSessionData] = useState<SessionData>({ loggedIn: false });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  useEffect(() => {    async function checkLogin() {
      const data = await fetchSession();
      setSessionData(data);
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

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const displayName = (() => {
    if (sessionData.user?.first_name && sessionData.user?.last_name) {
      return `${sessionData.user.first_name} ${sessionData.user.last_name}`;
    }
    if (sessionData.user?.first_name) {
      return sessionData.user.first_name;
    }
    if (sessionData.user?.name) {
      return sessionData.user.name;
    }
    return sessionData.user?.email?.split('@')[0] || 'User';
  })();

  return (
    <nav className="w-full flex items-center justify-between px-8 py-4 bg-white shadow mb-8">
      <div className="flex items-center gap-8">
        <Link href="/dashboard" className="text-xl font-bold text-blue-700 tracking-tight hover:text-blue-900 transition">CoachSync</Link>
        {sessionData.loggedIn && (
          <>
            <Link href="/dashboard" className="text-gray-700 font-medium hover:text-blue-700 transition">Dashboard</Link>
            <Link href="/timeline" className="text-gray-700 font-medium hover:text-blue-700 transition">Timeline</Link>
          </>
        )}
      </div>
      
      {sessionData.loggedIn ? (
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-blue-700 font-medium transition"
          >
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-semibold">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <span>{displayName}</span>
            <svg
              className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200">
              <Link
                href="/profile"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                onClick={() => setDropdownOpen(false)}
              >
                My Profile
              </Link>
              <Link
                href="/upload"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                onClick={() => setDropdownOpen(false)}
              >
                Upload Audio
              </Link>
              <hr className="my-1" />
              <Link
                href="/logout"
                className="block px-4 py-2 text-sm text-red-600 hover:bg-gray-100 transition"
                onClick={() => setDropdownOpen(false)}
              >
                Logout
              </Link>
            </div>
          )}
        </div>
      ) : (
        <Link href="/login" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold transition">Login</Link>
      )}
    </nav>
  );
}
