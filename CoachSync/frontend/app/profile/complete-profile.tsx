"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUserProfile, upsertUserProfile } from "../../lib/userApi";

export default function CompleteProfile() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    firstName: "",
    lastName: "",
    firefliesKey: "",
    zoomJwt: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch user profile from backend using email from localStorage or cookie
    const email = localStorage.getItem("userEmail");
    if (!email) {
      router.replace("/login");
      return;
    }
    getUserProfile(email).then((profile) => {
      const [firstName, ...rest] = (profile.name || "").split(" ");
      setForm({
        email: profile.email,
        firstName: firstName || "",
        lastName: rest.join(" ") || "",
        firefliesKey: profile.fireflies_api_key || "",
        zoomJwt: profile.zoom_jwt || "",
      });
      // If first or last name is missing, stay on this page
      if (!firstName || rest.length === 0) {
        setLoading(false);
      } else {
        // If profile is complete, redirect to dashboard
        router.replace("/dashboard");
      }
    }).catch(() => {
      setLoading(false);
    });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.firstName || !form.lastName) {
      setError("First and last name are required.");
      return;
    }
    try {
      await upsertUserProfile({
        email: form.email,
        name: form.firstName + " " + form.lastName,
        fireflies_api_key: form.firefliesKey || undefined,
        zoom_jwt: form.zoomJwt || undefined,
      });
      router.replace("/dashboard");
    } catch {
      setError("Failed to update profile. Try again.");
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen">Loading...</div>;

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Complete Your Profile</h2>
      <form className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100" onSubmit={handleSubmit}>
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="font-semibold text-gray-700">First Name</label>
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
            <label className="font-semibold text-gray-700">Last Name</label>
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
        <label className="font-semibold text-gray-700">Fireflies API Key <span className="font-normal text-gray-400">(optional)</span></label>
        <input
          type="text"
          className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={form.firefliesKey}
          onChange={e => setForm(f => ({ ...f, firefliesKey: e.target.value }))}
          placeholder="Enter your Fireflies API Key (optional)"
        />
        <label className="font-semibold text-gray-700">Zoom JWT <span className="font-normal text-gray-400">(optional)</span></label>
        <input
          type="text"
          className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={form.zoomJwt}
          onChange={e => setForm(f => ({ ...f, zoomJwt: e.target.value }))}
          placeholder="Enter your Zoom JWT (optional)"
        />
        {error && <div className="text-red-500 text-sm text-center">{error}</div>}
        <button type="submit" className="w-full bg-blue-600 text-white font-semibold rounded py-2 hover:bg-blue-700 transition">Save Profile</button>
      </form>
    </main>
  );
}
