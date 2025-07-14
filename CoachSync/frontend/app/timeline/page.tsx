"use client";

import { fetchSessions } from "../../lib/api";
import { useEffect, useState } from "react";

export default function Timeline() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      setLoading(false);
    });
  }, []);

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Timeline</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-2xl flex flex-col gap-6 border border-gray-100">
        {loading ? (
          <div>Loading...</div>
        ) : (
          <ul className="divide-y">
            {sessions.map((s, i) => (
              <li className="py-2" key={i}>
                <div className="font-semibold">Session {s.id}</div>
                <div className="text-gray-700 mt-1">{s.summary}</div>
              </li>
            ))}
          </ul>
        )}
        {/* Add your timeline content here, styled similarly */}
        <div className="text-gray-700 text-center">Timeline coming soon.</div>
      </div>
    </main>
  );
}