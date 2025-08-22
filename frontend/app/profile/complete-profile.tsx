"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { getApiUrl } from "../../lib/apiUrl";
import { authenticatedFetch } from "../../lib/authenticatedFetch";

interface User {
  email: string;
  name: string;
  first_name?: string;
  last_name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
}

export default function CompleteProfile() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [user, setUser] = useState<User | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [form, setForm] = useState({
    email: "",
    firstName: "",
    lastName: "",
    firefliesKey: "",
    zoomJwt: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Fetch user data using new session approach
  const fetchUser = useCallback(async () => {
    try {
      const response = await authenticatedFetch("/me");
      if (response.ok) {
        const userData = await response.json();
        const userProfile: User = {
          email: userData.email,
          name: userData.name || `${userData.first_name} ${userData.last_name}`.trim() || "User",
          first_name: userData.first_name || "",
          last_name: userData.last_name || "",
          fireflies_api_key: userData.fireflies_api_key || "",
          zoom_jwt: userData.zoom_jwt || "",
        };
        setUser(userProfile);
        return userProfile;
      } else {
        router.push('/login');
        return null;
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
      router.push('/login');
      return null;
    } finally {
      setUserLoading(false);
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    // Redirect to login if not authenticated
    if (status === "loading") return; // Still loading
    if (status === "unauthenticated") {
      router.push('/login');
      return;
    }
    if (status === "authenticated") {
      fetchUser();
    }
  }, [status, router, fetchUser]);

  useEffect(() => {
    async function fetchProfile() {
      try {
        // If user is not logged in, redirect to login
        if (!user) {
          router.replace("/login");
          return;
        }

        // Use user context for profile info
        setForm({
          email: user.email,
          firstName: user.first_name || "",
          lastName: user.last_name || "",
          firefliesKey: user.fireflies_api_key || "",
          zoomJwt: user.zoom_jwt || "",
        });

        // If profile is complete (has both names), redirect to dashboard
        if (user.first_name && user.last_name) {
          router.replace("/dashboard");
          return;
        }

        setLoading(false);
      } catch (err) {
        setError("Failed to load profile");
        setLoading(false);
      }
    }

    if (!userLoading) {
      fetchProfile();
    }
  }, [router, user, userLoading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.firstName || !form.lastName) {
      setError("First and last name are required.");
      return;
    }

    try {
      const res = await authenticatedFetch("/user", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: form.firstName,
          last_name: form.lastName,
          fireflies_api_key: form.firefliesKey || null,
          zoom_jwt: form.zoomJwt || null,
          }),
        }
      );

      if (res.ok) {
        router.replace("/dashboard");
      } else {
        setError("Failed to update profile. Try again.");
      }
    } catch {
      setError("Failed to update profile. Try again.");
    }
  }

  if (status === "loading" || loading || userLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-4">{error}</div>
      </div>
    );
  }
  // Only show complete-profile UI when not loading and no error
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Complete Your Profile</h2>
      <form className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100" onSubmit={handleSubmit}>
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
            <input
              type="text"
              className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 w-full"
              value={form.firstName}
              onChange={e => setForm(f => ({ ...f, firstName: e.target.value }))}
              placeholder="First name"
              required
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
            <input
              type="text"
              className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 w-full"
              value={form.lastName}
              onChange={e => setForm(f => ({ ...f, lastName: e.target.value }))}
              placeholder="Last name"
              required
            />
          </div>
        </div>
        
        <div className="border-t pt-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">API Integration (Optional)</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Fireflies.ai API Key
              </label>
              <input
                type="password"
                className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 w-full"
                value={form.firefliesKey}
                onChange={e => setForm(f => ({ ...f, firefliesKey: e.target.value }))}
                placeholder="Optional - for meeting transcription"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Zoom JWT Token
              </label>
              <input
                type="password"
                className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200 w-full"
                value={form.zoomJwt}
                onChange={e => setForm(f => ({ ...f, zoomJwt: e.target.value }))}
                placeholder="Optional - for Zoom integration"
              />
            </div>
          </div>
        </div>
        
        {error && (
          <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded text-center">
            {error}
          </div>
        )}
        
        <button 
          type="submit" 
          className="w-full bg-blue-600 text-white font-semibold rounded py-2 hover:bg-blue-700 transition"
        >
          Complete Profile
        </button>
      </form>
    </main>
  );
}
