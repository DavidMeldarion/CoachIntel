"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useUser } from "../../lib/userContext";

const API_BASE = process.env.NEXT_PUBLIC_BROWSER_API_URL || "http://localhost:8000";

function Dashboard() {
  const { user, loading: userLoading } = useUser();
  const [upcomingMeetings, setUpcomingMeetings] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [meetingStats, setMeetingStats] = useState({ total: 0, week: 0, month: 0, byType: {} as Record<string, number> });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState("");
  const [showReconnect, setShowReconnect] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        // Fetch meetings
        const meetingsRes = await fetch("/api/meetings", { credentials: "include" });
        const meetingsData = await meetingsRes.json();
        const meetings = meetingsData.meetings || [];

        // Fetch Google Calendar events
        let calendarEvents: any[] = [];
        try {
          const calRes = await fetch("/api/calendar/events", { credentials: "include" });
          if (calRes.ok) {
            const calData = await calRes.json();
            calendarEvents = calData.events || [];
          }
        } catch {}

        // Upcoming meetings: next 5 by date (from calendar, fallback to meetings)
        let upcoming = calendarEvents.map((e: any) => ({
          id: e.id,
          title: e.summary,
          date: e.start?.dateTime || e.start?.date,
          source: "Google Calendar"
        }));
        // If no calendar events, fallback to meetings
        if (upcoming.length === 0) {
          const now = new Date();
          upcoming = meetings
            .filter((m: any) => new Date(m.date) > now)
            .sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime())
            .slice(0, 5);
        }
        setUpcomingMeetings(upcoming.slice(0, 5));

        // Recent activity: last 5 meetings (by date desc)
        const recent = meetings
          .sort((a: any, b: any) => new Date(b.date).getTime() - new Date(a.date).getTime())
          .slice(0, 5)
          .map((m: any) => ({
            id: m.id,
            type: "Meeting",
            title: m.title,
            date: m.date,
            status: "Completed"
          }));
        setRecentActivity(recent);

        // Meeting stats
        const total = meetings.length;
        const weekStart = new Date();
        weekStart.setDate(weekStart.getDate() - weekStart.getDay());
        const now = new Date();
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
        const week = meetings.filter((m: any) => new Date(m.date) >= weekStart).length;
        const month = meetings.filter((m: any) => new Date(m.date) >= monthStart).length;
        const byType: Record<string, number> = {};
        meetings.forEach((m: any) => {
          byType[m.source] = (byType[m.source] || 0) + 1;
        });
        setMeetingStats({ total, week, month, byType });
      } catch (err) {
        setUpcomingMeetings([]);
        setRecentActivity([]);
        setMeetingStats({ total: 0, week: 0, month: 0, byType: {} });
      } finally {
        setLoading(false);
      }
    }
    if (!userLoading) fetchData();
  }, [userLoading]);

  // Helper: reconnect Google
  function handleReconnectGoogle() {
    window.location.href = "/login?reconnect=google";
  }

  async function handleSyncCalendar() {
    setSyncing(true);
    setSyncError("");
    try {
      const res = await fetch("/api/calendar/events", { credentials: "include" });
      const data = await res.json();
      if (!res.ok) {
        // Show backend error detail if available
        setSyncError(data.error ? `${data.error}${data.detail ? ": " + data.detail : ""}` : "Failed to sync calendar");
        // If token/auth error, show reconnect button
        if (data.error && (data.error.includes("token") || data.error.includes("authentication") || data.error.includes("Google Calendar token"))) {
          setShowReconnect(true);
        } else {
          setShowReconnect(false);
        }
        return;
      }
      setShowReconnect(false);
      // Optionally update upcomingMeetings with new events
      if (data.events) {
        const upcoming = data.events.map((e: any) => ({
          id: e.id,
          title: e.summary,
          date: e.start?.dateTime || e.start?.date,
          source: "Google Calendar"
        }));
        setUpcomingMeetings(upcoming.slice(0, 5));
      }
    } catch (err: any) {
      setSyncError(err.message || "Sync failed");
      setShowReconnect(false);
    } finally {
      setSyncing(false);
    }
  }

  async function handleSyncMeetings() {
    setSyncing(true);
    setSyncError("");
    try {
      let res = await fetch("/api/external-meetings?source=fireflies&limit=10", { credentials: "include" });
      let data = await res.json();
      console.log("[Dashboard DEBUG] /api/external-meetings response:", data);
      if (data.error && data.error.includes("Fireflies API key not found")) {
        res = await fetch("/api/external-meetings?source=zoom&limit=10", { credentials: "include" });
        data = await res.json();
        console.log("[Dashboard DEBUG] /api/external-meetings (zoom) response:", data);
      }
      if (data.meetings && Array.isArray(data.meetings)) {
        setRecentActivity(data.meetings.slice(0, 5));
        if (data.meetings.length === 0) {
          setSyncError("No meetings found. Try syncing again or check your Fireflies account.");
        }
      } else {
        setSyncError("No meetings array in response. Raw response: " + JSON.stringify(data));
      }
    } catch (err) {
      setSyncError("Sync failed: " + (err?.message || err));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Dashboard</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl flex flex-col gap-8 border border-gray-100">
        {/* 1. Welcome Header */}
        <div className="flex flex-col items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-800">Welcome, {user?.name || "User"}!</h3>
          <p className="text-gray-600 mt-1">Here's a quick summary of your activity.</p>
        </div>
        {/* Quick Actions */}
        <div className="flex gap-4 mb-6">
          <Link href="/upload">
            <button className="px-4 py-2 rounded bg-blue-600 text-white font-semibold transition hover:bg-blue-700">Upload Audio</button>
          </Link>
          <button
            className="px-4 py-2 rounded bg-green-600 text-white font-semibold transition hover:bg-green-700"
            onClick={handleSyncCalendar}
            disabled={syncing}
          >
            {syncing ? "Syncing..." : "Sync Google Calendar"}
          </button>
          <button
            className="px-4 py-2 rounded bg-purple-600 text-white font-semibold transition hover:bg-purple-700"
            onClick={handleSyncMeetings}
            disabled={syncing}
          >
            {syncing ? "Syncing..." : "Sync Transcribed Meetings (Fireflies/Zoom)"}
          </button>
          {showReconnect && (
            <button
              className="px-4 py-2 rounded bg-red-600 text-white font-semibold transition hover:bg-red-700"
              onClick={handleReconnectGoogle}
            >
              Reconnect Google
            </button>
          )}
        </div>
        {syncError && <div className="text-red-600 text-sm mb-2">{syncError}</div>}
        {/* 2. Upcoming Meetings */}
        <div>
          <h4 className="text-lg font-semibold mb-2 text-blue-700">Upcoming Meetings</h4>
          {loading ? (
            <div className="text-gray-500">Loading...</div>
          ) : upcomingMeetings.length > 0 ? (
            <ul className="divide-y">
              {upcomingMeetings.map(m => (
                <li key={m.id} className="py-2 flex justify-between items-center">
                  <span className="font-medium text-gray-800">{m.title}</span>
                  <span className="text-gray-500 text-sm">{m.date}</span>
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs ml-2">{m.source}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-gray-500">No upcoming meetings.</div>
          )}
        </div>
        {/* 3. Recent Activity */}
        <div>
          <h4 className="text-lg font-semibold mb-2 text-blue-700">Recent Activity</h4>
          {loading ? (
            <div className="text-gray-500">Loading...</div>
          ) : recentActivity.length > 0 ? (
            <ul className="divide-y">
              {recentActivity.map(a => (
                <li key={a.id} className="py-2 flex items-center justify-between">
                  <span className="font-medium text-gray-800 flex-1">{a.title}</span>
                  <span className="text-gray-500 text-sm flex-1 text-center">{a.date}</span>
                  <span className={`px-2 py-1 rounded text-xs ml-2 text-center ${a.status === 'Completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`} style={{ display: 'inline-block', minWidth: '80px' }}>{a.status}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-gray-500">No recent activity.</div>
          )}
        </div>
        {/* 4. Meeting Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 flex flex-col items-center">
            <span className="text-3xl font-bold text-blue-700">{meetingStats.total}</span>
            <span className="text-gray-700">Total Meetings</span>
          </div>
          <div className="bg-green-50 rounded-lg p-4 flex flex-col items-center">
            <span className="text-xl font-bold text-green-700">{meetingStats.week}</span>
            <span className="text-gray-700">This Week</span>
            <span className="text-xl font-bold text-green-700 mt-2">{meetingStats.month}</span>
            <span className="text-gray-700">This Month</span>
          </div>
          <div className="col-span-2 bg-gray-50 rounded-lg p-4 mt-2">
            <span className="font-semibold text-gray-700">By Type:</span>
            <div className="flex gap-4 mt-2">
              {Object.entries(meetingStats.byType).map(([type, count]) => (
                <div key={type} className="bg-white border rounded px-3 py-1 text-sm text-gray-700">
                  {type}: <span className="font-bold text-blue-700">{String(count)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default Dashboard;