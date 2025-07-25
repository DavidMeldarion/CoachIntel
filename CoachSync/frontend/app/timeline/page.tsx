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
  const [keyword, setKeyword] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedParticipant, setSelectedParticipant] = useState<string>("");
  const [currentPage, setCurrentPage] = useState(1);
  const [meetingsPerPage, setMeetingsPerPage] = useState(10);

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

  // Get unique client names, meeting types, and participants
  const clientNames = Array.from(new Set(sortedMeetings.map((m) => m.client_name).filter(Boolean)));
  const meetingTypes = Array.from(new Set(sortedMeetings.map((m) => m.source).filter(Boolean)));
  const participants = Array.from(new Set(sortedMeetings.flatMap(m => m.participants || []).filter(Boolean)));

  // Filter meetings by all criteria
  const filteredMeetings = sortedMeetings.filter((m) => {
    const clientMatch = selectedClient ? m.client_name === selectedClient : true;
    const typeMatch = selectedType ? m.source === selectedType : true;
    const participantMatch = selectedParticipant ? (m.participants || []).includes(selectedParticipant) : true;
    const keywordMatch = keyword ? (
      (m.transcript?.summary?.keywords?.some((k: string) => k.toLowerCase().includes(keyword.toLowerCase())) || false) ||
      (m.transcript?.summary?.overview?.toLowerCase().includes(keyword.toLowerCase()) || false)
    ) : true;
    const dateMatch = (() => {
      if (startDate && new Date(m.date) < new Date(startDate)) return false;
      if (endDate && new Date(m.date) > new Date(endDate)) return false;
      return true;
    })();
    return clientMatch && typeMatch && participantMatch && keywordMatch && dateMatch;
  });

  // Pagination logic
  const totalMeetings = filteredMeetings.length;
  const totalPages = Math.ceil(totalMeetings / meetingsPerPage);
  const paginatedMeetings = filteredMeetings.slice((currentPage - 1) * meetingsPerPage, currentPage * meetingsPerPage);

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
      {/* Loading and error states */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-2"></span>
          <span className="text-gray-500">Loading meetings...</span>
        </div>
      )}
      {error && !loading && (
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-4">{error}</div>
      )}
      {/* Only show timeline UI when not loading and no error */}
      {!loading && !error && (
        <>
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
                  <label htmlFor="client-filter" className="font-medium text-gray-700">Client:</label>
                  <select
                    id="client-filter"
                    className="border rounded px-2 py-1 text-sm"
                    value={selectedClient}
                    onChange={(e) => { setSelectedClient(e.target.value); setCurrentPage(1); }}
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
                  <label htmlFor="type-filter" className="font-medium text-gray-700">Type:</label>
                  <select
                    id="type-filter"
                    className="border rounded px-2 py-1 text-sm"
                    value={selectedType}
                    onChange={(e) => { setSelectedType(e.target.value); setCurrentPage(1); }}
                  >
                    <option value="">All</option>
                    {meetingTypes.map((type) => (
                      <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                    ))}
                  </select>
                </div>
              )}
              {participants.length > 1 && (
                <div className="flex items-center gap-2">
                  <label htmlFor="participant-filter" className="font-medium text-gray-700">Participant:</label>
                  <select
                    id="participant-filter"
                    className="border rounded px-2 py-1 text-sm"
                    value={selectedParticipant}
                    onChange={(e) => { setSelectedParticipant(e.target.value); setCurrentPage(1); }}
                  >
                    <option value="">All</option>
                    {participants.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex items-center gap-2">
                <label htmlFor="keyword-search" className="font-medium text-gray-700">Keyword:</label>
                <input
                  id="keyword-search"
                  type="text"
                  className="border rounded px-2 py-1 text-sm"
                  value={keyword}
                  onChange={e => { setKeyword(e.target.value); setCurrentPage(1); }}
                  placeholder="Search keywords or overview"
                />
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="start-date" className="font-medium text-gray-700">From:</label>
                <input
                  id="start-date"
                  type="date"
                  className="border rounded px-2 py-1 text-sm"
                  value={startDate}
                  onChange={e => { setStartDate(e.target.value); setCurrentPage(1); }}
                />
                <label htmlFor="end-date" className="font-medium text-gray-700">To:</label>
                <input
                  id="end-date"
                  type="date"
                  className="border rounded px-2 py-1 text-sm"
                  value={endDate}
                  onChange={e => { setEndDate(e.target.value); setCurrentPage(1); }}
                />
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="meetings-per-page" className="font-medium text-gray-700">Per page:</label>
                <select
                  id="meetings-per-page"
                  className="border rounded px-2 py-1 text-sm"
                  value={meetingsPerPage}
                  onChange={e => { setMeetingsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                >
                  {[5, 10, 20, 50].map(n => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </div>
            </div>
            {/* Meeting list with pagination */}
            <div className="max-h-[600px] overflow-y-auto">
              {paginatedMeetings.length > 0 ? (
                <div className="space-y-4">
                  {paginatedMeetings.map((meeting: any) => (
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
                      {meeting.participants && meeting.participants.length > 0 && (
                        <div className="mb-3">
                          <strong>Participants:</strong> {meeting.participants.join(", ")}
                        </div>
                      )}
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
                      <div className="mt-4">
                        <a
                          href={`/timeline/${meeting.id}`}
                          className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                        >
                          View Full Transcript
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-center py-4">No meetings found</div>
              )}
            </div>
            {/* Pagination controls */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-4 mt-6">
                <button
                  className="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold disabled:opacity-50"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                <span className="font-medium text-gray-700">Page {currentPage} of {totalPages}</span>
                <button
                  className="px-3 py-1 rounded bg-gray-200 text-gray-700 font-semibold disabled:opacity-50"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </main>
  );
}