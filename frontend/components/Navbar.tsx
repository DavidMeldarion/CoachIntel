"use client";
import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { useSession, signOut } from "next-auth/react";

export default function Navbar() {
  const { data: session, status } = useSession();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const loading = status === "loading";
  const loggedIn = !!session?.user;

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
    if (!session?.user) return 'User';
    
    // NextAuth user structure: { name, email, image }
    if (session.user.name) {
      return session.user.name;
    }
    return session.user.email?.split('@')[0] || 'User';
  })();

  // Handle logout: use NextAuth signOut
  const handleLogout = async () => {
    console.log('[Navbar] Logout clicked');
    setDropdownOpen(false);
    
    try {
      console.log('[Navbar] Calling NextAuth signOut');
      await signOut({ 
        callbackUrl: '/login',
        redirect: true 
      });
    } catch (err) {
      console.error("Navbar: Logout failed", err);
      // Fallback: redirect to login anyway
      window.location.href = "/login";
    }
  };

  const currentPlan = (session as any)?.user?.plan as 'free'|'plus'|'pro'|undefined;
  const purchaseHref = currentPlan ? `/purchase?current=${currentPlan}` : '/purchase';

  const siteAdmin = (session as any)?.siteAdmin === true;
  const orgAdminIds = ((session as any)?.orgAdminIds as number[] | undefined) || [];
  const canSeeAdmin = siteAdmin || orgAdminIds.length > 0;

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
            {canSeeAdmin && (
              <Link href="/admin/leads" className="text-gray-700 font-medium hover:text-blue-700 transition">Admin</Link>
            )}
          </>
        )}
      </div>
      
      {loggedIn ? (
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-blue-700 font-medium transition"
          >
            <div className="w-8 h-8 ci-bg-primary ci-text-white rounded-full flex items-center justify-center text-sm font-semibold">
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
              <Link
                href={purchaseHref}
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                onClick={() => setDropdownOpen(false)}
              >
                Upgrade
              </Link>
              {canSeeAdmin && (
                <Link
                  href="/admin/leads"
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition"
                  onClick={() => setDropdownOpen(false)}
                >
                  Admin
                </Link>
              )}
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
  <Link href="/login" className="px-4 py-2 ci-bg-primary ci-text-white rounded hover:ci-bg-primary font-semibold transition">Login</Link>
      )}
    </nav>
  );
}
