"use client";

import { fetchSessions } from "../../lib/api";
import { useEffect, useState } from "react";
import { useSync } from "../../lib/syncContext";

export default function MeetingTimeline() {
  const { lastSync } = useSync();
  const [meetings, setMeetings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedClient, setSelectedClient] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");

  // Fetch stored meetings from backend
  const fetchStoredMeetings = async () => {
    setLoading(true);
    setError("");
    try {
      // Add cache-busting param to always get fresh data
      const response = await fetch(`/api/meetings?ts=${Date.now()}`, { credentials: "include" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMeetings(data.meetings || []);
    } catch (err) {
      setError(`Failed to fetch meetings: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh meetings every 5 minutes
  useEffect(() => {
    fetchStoredMeetings();
    const interval = setInterval(fetchStoredMeetings, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Refetch meetings when lastSync changes
  useEffect(() => {
    fetchStoredMeetings();
  }, [lastSync]);

  // Sort meetings by date descending (most recent first)
  const sortedMeetings = [...meetings].sort((a, b) => {
    const dateA = new Date(a.date).getTime();
    const dateB = new Date(b.date).getTime();
    return dateB - dateA;
  });

  // Get unique client names and meeting types from sorted meetings
  const clientNames = Array.from(new Set(sortedMeetings.map((m) => m.client_name).filter(Boolean)));
  const meetingTypes = Array.from(new Set(sortedMeetings.map((m) => m.source).filter(Boolean)));

  // Filter meetings by selected client and type
  const filteredMeetings = sortedMeetings.filter((m) => {
    const clientMatch = selectedClient ? m.client_name === selectedClient : true;
    const typeMatch = selectedType ? m.source === selectedType : true;
    return clientMatch && typeMatch;
  });

  // Helper to format date in a user-friendly way
  function formatDate(dateStr: string) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true
    });
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Meeting Timeline</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl border border-gray-100">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Your Meetings</h3>
          <button
            className="px-3 py-1 rounded bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700"
            onClick={fetchStoredMeetings}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {/* Filters */}
        <div className="mb-4 flex flex-wrap gap-4 items-center">
          {clientNames.length > 1 && (
            <div className="flex items-center gap-2">
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
          {meetingTypes.length > 1 && (
            <div className="flex items-center gap-2">
              <label htmlFor="type-filter" className="font-medium text-gray-700">Filter by type:</label>
              <select
                id="type-filter"
                className="border rounded px-2 py-1 text-sm"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
              >
                <option value="">All</option>
                {meetingTypes.map((type) => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="max-h-[600px] overflow-y-auto">
          {loading ? (
            <div>Loading meetings...</div>
          ) : error ? (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">{error}</div>
          ) : filteredMeetings.length > 0 ? (
            <div className="space-y-4">
              {filteredMeetings.map((meeting: any) => (
                <div key={meeting.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-semibold text-lg">{meeting.title}</h4>
                    <span className="text-sm text-gray-500">{formatDate(meeting.date)}</span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    Duration: {Math.floor(meeting.duration / 60)}m {meeting.duration % 60}s
                  </div>
                  <div className="mb-3">
                    <strong>Client:</strong> {meeting.client_name}
                  </div>
                  <div className="mb-3">
                    <strong>Type:</strong> {meeting.source ? meeting.source.charAt(0).toUpperCase() + meeting.source.slice(1) : "Unknown"}
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