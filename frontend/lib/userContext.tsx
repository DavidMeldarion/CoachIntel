"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiUrl } from "./apiUrl";

export type User = {
  email: string;
  name: string;
  first_name?: string;
  last_name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
  phone?: string;
  address?: string;
};

const UserContext = createContext<{ 
  user: User | null; 
  loading: boolean; 
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
}>({ 
  user: null, 
  loading: true, 
  refreshUser: async () => {}, 
  logout: async () => {}
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUser = async () => {
    console.log("UserProvider: fetchUser called");
    console.log("UserProvider: document.cookie =", document.cookie);
    setLoading(true);
    let didFinish = false;
    try {
      const res = await fetch(getApiUrl("/me"), { 
        credentials: "include",
        cache: "no-cache", // Prevent caching
        headers: {
          "Cache-Control": "no-cache"
        }
      });
      console.log("UserProvider: /me response status:", res.status, res.ok);
      if (!res.ok) {
        console.log("UserProvider: Setting user to null due to !res.ok");
        setUser(null);
        didFinish = true;
        return;
      }
      const user = await res.json();
      console.log("UserProvider: /me response data:", user);
      setUser({
        email: user.email,
        name: user.name || `${user.first_name} ${user.last_name}`.trim() || "User",
        first_name: user.first_name,
        last_name: user.last_name,
        fireflies_api_key: user.fireflies_api_key,
        zoom_jwt: user.zoom_jwt,
        phone: user.phone,
        address: user.address,
      });
      didFinish = true;
    } catch (err) {
      console.error("UserProvider: Error fetching user", err);
      setUser(null);
      didFinish = true;
    } finally {
      setLoading(false);
    }
    setTimeout(() => {
      if (!didFinish) {
        console.error("UserProvider: fetchUser timeout fallback triggered");
        setLoading(false);
      }
    }, 5000);
  };

  // Background session/token check (every 5 min)
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(getApiUrl("/calendar/events"), { credentials: "include" });
        if (res.status === 401) {
          await fetch(getApiUrl('/logout'), { method: 'POST' });
          localStorage.clear();
          sessionStorage.clear();
          router.replace("/login");
        }
      } catch {
        // Silently ignore errors
      }
    }, 5 * 60 * 1000); // 5 minutes
    return () => clearInterval(interval);
  }, [user, router]);

  useEffect(() => {
    // console.log("UserProvider: useEffect running");
    fetchUser();
  }, []);

  const logout = async () => {
    console.log("UserProvider: logout called - immediately clearing user state");
    setUser(null);
    setLoading(false);
    
    try {
      // Call logout API
      await fetch('/api/logout', { method: 'POST' });
      console.log("UserProvider: logout API called successfully");
    } catch (error) {
      console.error("UserProvider: logout API failed", error);
    }
    
    // Clear storage
    localStorage.clear();
    sessionStorage.clear();
  };

//   console.log("UserProvider: rendering", { user, loading });
  return <UserContext.Provider value={{ user, loading, refreshUser: fetchUser, logout }}>{children}</UserContext.Provider>;
}

export function useUser() {
  return useContext(UserContext);
}
