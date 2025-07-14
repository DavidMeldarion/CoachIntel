"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { upsertUserProfile } from "../../lib/userApi";

export default function ApiKeys() {
  const [firefliesKey, setFirefliesKey] = useState("");
  const [zoomJwt, setZoomJwt] = useState("");
  const [status, setStatus] = useState("");
  const router = useRouter();

  // Client-side auth check for extra security
  useEffect(() => {
    if (typeof document !== 'undefined') {
      const cookies = document.cookie.split(';').map(c => c.trim());
      const userCookie = cookies.find(c => c.startsWith('user='));
      if (!userCookie) {
        router.replace("/login?redirect=/apikeys");
      }
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Saving and testing keys...");
    try {
      // Save to backend
      const email = localStorage.getItem("userEmail") || "";
      await upsertUserProfile({ email, fireflies_api_key: firefliesKey, zoom_jwt: zoomJwt });
      // Test Fireflies
      let firefliesOk = false;
      if (firefliesKey) {
        const res = await fetch(`/api/test-fireflies?key=${encodeURIComponent(firefliesKey)}`);
        firefliesOk = res.ok;
      }
      // Test Zoom
      let zoomOk = false;
      if (zoomJwt) {
        const res = await fetch(`/api/test-zoom?jwt=${encodeURIComponent(zoomJwt)}`);
        zoomOk = res.ok;
      }
      if (firefliesKey) localStorage.setItem("firefliesKey", firefliesKey);
      if (zoomJwt) localStorage.setItem("zoomJwt", zoomJwt);
      setStatus(`Profile saved. Fireflies: ${firefliesOk ? "OK" : "Failed"}, Zoom: ${zoomOk ? "OK" : "Failed"}`);
    } catch (err) {
      setStatus("Error saving profile or testing keys");
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">API Keys</h2>
      <form className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100" onSubmit={handleSubmit}>
        <label className="font-semibold text-gray-700">Fireflies API Key</label>
        <input
          type="text"
          className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={firefliesKey}
          onChange={e => setFirefliesKey(e.target.value)}
          placeholder="Enter your Fireflies API Key"
        />
        <label className="font-semibold text-gray-700">Zoom JWT</label>
        <input
          type="text"
          className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={zoomJwt}
          onChange={e => setZoomJwt(e.target.value)}
          placeholder="Enter your Zoom JWT"
        />
        <button type="submit" className="w-full bg-blue-600 text-white font-semibold rounded py-2 hover:bg-blue-700 transition">Save Keys</button>
        {status && <div className="mt-2 text-sm text-center">{status}</div>}
      </form>
    </main>
  );
}
