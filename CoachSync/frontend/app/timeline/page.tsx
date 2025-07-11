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
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <h2 className="text-2xl font-bold mb-4">Session Timeline</h2>
      <div className="w-full max-w-md bg-white rounded shadow p-6">
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
      </div>
    </main>
  );
}