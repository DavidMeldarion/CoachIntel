"use client";
import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { useUser } from "../lib/userContext";

export default function Navbar() {
  const { user, loading, refreshUser } = useUser();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const loggedIn = !!user;

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
    if (user?.first_name && user?.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    if (user?.first_name) {
      return user.first_name;
    }
    if (user?.name) {
      return user.name;
    }
    return user?.email?.split('@')[0] || 'User';
  })();

  // Handle logout: call refreshUser after navigation
  const handleLogout = async () => {
    setDropdownOpen(false);
    try {
      await fetch("/api/logout", { method: "POST", credentials: "include" });
    } catch (err) {
      console.error("Navbar: Logout failed", err);
    }
    await refreshUser();
    window.location.href = "/login";
  };

  if (loading) {
    return (
      <nav className="w-full flex items-center justify-between px-8 py-4 bg-white shadow mb-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-xl font-bold text-blue-700 tracking-tight hover:text-blue-900 transition">CoachIntel</Link>
        </div>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
      </nav>
    );
  }

  return (
    <nav className="w-full flex items-center justify-between px-8 py-4 bg-white shadow mb-8">
      <div className="flex items-center gap-8">
        <Link href="/" className="text-xl font-bold text-blue-700 tracking-tight hover:text-blue-900 transition">CoachIntel</Link>
        {loggedIn && (
          <>
            <Link href="/dashboard" className="text-gray-700 font-medium hover:text-blue-700 transition">Dashboard</Link>
            <Link href="/timeline" className="text-gray-700 font-medium hover:text-blue-700 transition">Meeting Timeline</Link>
          </>
        )}
      </div>
      
      {loggedIn ? (
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
              <button
                onClick={handleLogout}
                className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 transition"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      ) : (
        <Link href="/login" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold transition">Login</Link>
      )}
    </nav>
  );
}
