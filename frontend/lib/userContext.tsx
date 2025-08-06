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

const UserContext = createContext<{ user: User | null; loading: boolean; refreshUser: () => Promise<void> }>({ user: null, loading: true, refreshUser: async () => {} });

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUser = async () => {
    // console.log("UserProvider: fetchUser called");
    setLoading(true);
    let didFinish = false;
    try {
      const res = await fetch(getApiUrl("/session"), { credentials: "include" });
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        // console.error("UserProvider: Failed to parse /api/session response", text);
        setUser(null);
        didFinish = true;
        return;
      }
    //   console.debug("UserProvider: /api/session response", data);
      if (data.loggedIn && data.user) {
        setUser({
          email: data.user.email,
          name: data.user.name || data.user.first_name || "User",
          first_name: data.user.first_name,
          last_name: data.user.last_name,
          fireflies_api_key: data.user.fireflies_api_key,
          zoom_jwt: data.user.zoom_jwt,
          phone: data.user.phone,
          address: data.user.address,
        });
      } else {
        setUser(null);
      }
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

//   console.log("UserProvider: rendering", { user, loading });
  return <UserContext.Provider value={{ user, loading, refreshUser: fetchUser }}>{children}</UserContext.Provider>;
}

export function useUser() {
  return useContext(UserContext);
}
