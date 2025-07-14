"use client";
import { useEffect, useState } from "react";
import { getUserProfile, upsertUserProfile } from "../../lib/userApi";
import { useRouter } from "next/navigation";

export default function Profile() {
  const [profile, setProfile] = useState({
    email: "",
    name: "",
    phone: "",
    address: "",
    fireflies_api_key: "",
    zoom_jwt: "",
  });
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const email = localStorage.getItem("userEmail") || "";
    if (!email) {
      router.replace("/login");
      return;
    }
    getUserProfile(email)
      .then((data) => {
        setProfile({
          email: data.email,
          name: data.name || "",
          phone: data.phone || "",
          address: data.address || "",
          fireflies_api_key: data.fireflies_api_key || "",
          zoom_jwt: data.zoom_jwt || "",
        });
        setLoading(false);
      })
      .catch(() => {
        setStatus("No profile found. Please complete your info.");
        setProfile((p) => ({ ...p, email }));
        setLoading(false);
      });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Saving...");
    try {
      await upsertUserProfile(profile);
      setStatus("Profile updated!");
    } catch (err) {
      setStatus("Error saving profile");
    }
  }

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Profile</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="font-semibold">Email</label>
          <input
            type="email"
            className="border rounded p-2 bg-gray-100"
            value={profile.email}
            disabled
          />
          <label className="font-semibold">Name</label>
          <input
            type="text"
            className="border rounded p-2"
            value={profile.name}
            onChange={e => setProfile(p => ({ ...p, name: e.target.value }))}
            placeholder="Enter your name"
          />
          <label className="font-semibold">Phone</label>
          <input
            type="text"
            className="border rounded p-2"
            value={profile.phone}
            onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))}
            placeholder="Enter your phone number"
          />
          <label className="font-semibold">Address</label>
          <input
            type="text"
            className="border rounded p-2"
            value={profile.address}
            onChange={e => setProfile(p => ({ ...p, address: e.target.value }))}
            placeholder="Enter your address"
          />
          <div className="border-t pt-4 mt-4">
            <label className="font-semibold">Fireflies API Key</label>
            <input
              type="text"
              className="border rounded p-2"
              value={profile.fireflies_api_key}
              onChange={e => setProfile(p => ({ ...p, fireflies_api_key: e.target.value }))}
              placeholder="Enter your Fireflies API Key"
            />
            <label className="font-semibold">Zoom JWT</label>
            <input
              type="text"
              className="border rounded p-2"
              value={profile.zoom_jwt}
              onChange={e => setProfile(p => ({ ...p, zoom_jwt: e.target.value }))}
              placeholder="Enter your Zoom JWT"
            />
          </div>
          <button type="submit" className="btn-primary">Save Profile</button>
          {status && <div className="mt-2 text-sm">{status}</div>}
        </form>
        <div className="text-gray-700 text-center">Profile details coming soon.</div>
      </div>
    </main>
  );
}
