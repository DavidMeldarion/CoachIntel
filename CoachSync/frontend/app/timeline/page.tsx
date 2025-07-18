"use client";

import { fetchSessions } from "../../lib/api";
import { useEffect, useState } from "react";

export default function Timeline() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [meetings, setMeetings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedClient, setSelectedClient] = useState<string>("");

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      setLoading(false);
    });
  }, []);

  // Fetch stored meetings from backend
  const fetchStoredMeetings = async () => {
    setMeetingsLoading(true);
    setError("");
    try {
      const response = await fetch("/api/meetings", { credentials: "include" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMeetings(data.meetings || []);
    } catch (err) {
      setError(`Failed to fetch meetings: ${err}`);
    } finally {
      setMeetingsLoading(false);
    }
  };

  // Auto-refresh meetings every 5 minutes
  useEffect(() => {
    fetchStoredMeetings();
    const interval = setInterval(fetchStoredMeetings, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Get unique client names from meetings
  const clientNames = Array.from(new Set(meetings.map((m) => m.client_name).filter(Boolean)));

  // Filter meetings by selected client
  const filteredMeetings = selectedClient
    ? meetings.filter((m) => m.client_name === selectedClient)
    : meetings;

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Timeline</h2>
      
      {/* Sessions Section */}
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl mb-6 border border-gray-100">
        <h3 className="text-lg font-semibold mb-4">Uploaded Sessions</h3>
        {loading ? (
          <div>Loading sessions...</div>
        ) : (
          <ul className="divide-y">
            {sessions.length > 0 ? sessions.map((s, i) => (
              <li className="py-2" key={i}>
                <div className="font-semibold">Session {s.id}</div>
                <div className="text-gray-700 mt-1">{s.summary}</div>
              </li>
            )) : (
              <div className="text-gray-500 text-center py-4">No uploaded sessions found</div>
            )}
          </ul>
        )}
      </div>

      {/* Meetings Section */}
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl border border-gray-100">
        <h3 className="text-lg font-semibold mb-4">Your Meetings</h3>
        {/* Client Filter Dropdown */}
        {clientNames.length > 1 && (
          <div className="mb-4 flex items-center gap-2">
            <label htmlFor="client-filter" className="font-medium text-gray-700">Filter by client:</label>
            <select
              id="client-filter"
              className="border rounded px-2 py-1 text-sm"
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
            >
              <option value="">All</option>
              {clientNames.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
        )}
        <div className="max-h-[600px] overflow-y-auto">
          {meetingsLoading ? (
            <div>Loading meetings...</div>
          ) : error ? (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">{error}</div>
          ) : filteredMeetings.length > 0 ? (
            <div className="space-y-4">
              {filteredMeetings.map((meeting: any) => (
                <div key={meeting.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-semibold text-lg">{meeting.title}</h4>
                    <span className="text-sm text-gray-500">{meeting.date}</span>
                  </div>
                  
                  <div className="text-sm text-gray-600 mb-2">
                    Duration: {Math.floor(meeting.duration / 60)}m {meeting.duration % 60}s
                  </div>
                  
                  <div className="mb-3">
                    <strong>Client:</strong> {meeting.client_name}
                  </div>
                  
                  {meeting.transcript?.summary?.overview && (
                    <div className="mb-3">
                      <strong>Overview:</strong>
                      <p className="text-gray-700 mt-1">{meeting.transcript.summary.overview}</p>
                    </div>
                  )}
                  
                  {meeting.transcript?.summary?.keywords?.length > 0 && (
                    <div className="mb-3">
                      <strong>Keywords:</strong>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {meeting.transcript.summary.keywords.map((keyword: string, i: number) => (
                          <span key={i} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">{keyword}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {meeting.transcript?.summary?.action_items?.length > 0 && (
                    <div>
                      <strong>Action Items:</strong>
                      <ul className="list-disc list-inside mt-1 text-gray-700">
                        {meeting.transcript.summary.action_items.map((item: string, i: number) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-4">No meetings found</div>
          )}
        </div>
      </div>
    </main>
  );
}