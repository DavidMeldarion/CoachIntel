"use client";

import { fetchSessions } from "../../lib/api";
import { useEffect, useState } from "react";

interface FirefliesMeeting {
  id: string;
  title: string;
  date: string;
  duration: number;
  participants: Array<{ name: string; email: string }>;
  summary: {
    overview: string;
    keywords: string[];
    action_items: string[];
    key_points: string[];
  };
  source: string;
}

interface FirefliesResponse {
  meetings: FirefliesMeeting[];
  total_count: number;
  source: string;
  error?: string;
}

export default function Timeline() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [firefliesMeetings, setFirefliesMeetings] = useState<FirefliesMeeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      setLoading(false);
    });
  }, []);

  const fetchFirefliesMeetings = async () => {
    if (!userEmail) {
      setError("Please enter your email address");
      return;
    }

    setMeetingsLoading(true);
    setError("");
    
    try {
      const response = await fetch(
        `/api/external-meetings?source=fireflies&user=${encodeURIComponent(userEmail)}&limit=10`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data: FirefliesResponse = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setFirefliesMeetings(data.meetings || []);
      }
    } catch (err) {
      setError(`Failed to fetch Fireflies meetings: ${err}`);
    } finally {
      setMeetingsLoading(false);
    }
  };

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

      {/* Fireflies Integration Section */}
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl border border-gray-100">
        <h3 className="text-lg font-semibold mb-4">Fireflies.ai Meetings</h3>
        
        <div className="mb-4 flex gap-3">
          <input
            type="email"
            placeholder="Enter your email address"
            value={userEmail}
            onChange={(e) => setUserEmail(e.target.value)}
            className="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
          <button
            onClick={fetchFirefliesMeetings}
            disabled={meetingsLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {meetingsLoading ? "Loading..." : "Fetch Meetings"}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {firefliesMeetings.length > 0 && (
          <div className="space-y-4">
            {firefliesMeetings.map((meeting) => (
              <div key={meeting.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-lg">{meeting.title}</h4>
                  <span className="text-sm text-gray-500">{meeting.date}</span>
                </div>
                
                <div className="text-sm text-gray-600 mb-2">
                  Duration: {Math.floor(meeting.duration / 60)}m {meeting.duration % 60}s
                </div>
                
                <div className="mb-3">
                  <strong>Participants:</strong> {' '}
                  {meeting.participants.map(p => p.name).join(", ")}
                </div>
                
                {meeting.summary.overview && (
                  <div className="mb-3">
                    <strong>Overview:</strong>
                    <p className="text-gray-700 mt-1">{meeting.summary.overview}</p>
                  </div>
                )}
                
                {meeting.summary.keywords.length > 0 && (
                  <div className="mb-3">
                    <strong>Keywords:</strong>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {meeting.summary.keywords.map((keyword, i) => (
                        <span key={i} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {meeting.summary.action_items.length > 0 && (
                  <div>
                    <strong>Action Items:</strong>
                    <ul className="list-disc list-inside mt-1 text-gray-700">
                      {meeting.summary.action_items.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        
        {firefliesMeetings.length === 0 && !meetingsLoading && !error && (
          <div className="text-gray-500 text-center py-4">
            Enter your email and click "Fetch Meetings" to load your Fireflies meetings
          </div>
        )}
      </div>
    </main>
  );
}