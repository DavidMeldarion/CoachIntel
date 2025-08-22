"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useSync } from "../../lib/syncContext";
import { getApiUrl } from "../../lib/apiUrl";
import { authenticatedFetch } from "../../lib/authenticatedFetch";

interface User {
  email: string;
  name: string;
  first_name?: string;
  last_name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
  phone?: string;
  address?: string;
}

function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { triggerSync } = useSync();
  const [user, setUser] = useState<User | null>(null);
  const userLoading = status === "loading";
  const [upcomingMeetings, setUpcomingMeetings] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [meetingStats, setMeetingStats] = useState({ total: 0, week: 0, month: 0, byType: {} as Record<string, number> });
  const [loading, setLoading] = useState(true);        // initial load only
  const [refreshing, setRefreshing] = useState(false); // background refresh after actions
  const [syncingCalendar, setSyncingCalendar] = useState(false);
  const [syncingMeetings, setSyncingMeetings] = useState(false);
  const [syncError, setSyncError] = useState("");
  const [showReconnect, setShowReconnect] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (status === "unauthenticated") {
      window.location.href = '/login';
    }
  }, [status]);

  // Fetch user data from backend when session is available
  useEffect(() => {
    if (!session?.user || status === "loading") return;

    async function fetchUser() {
      try {
        const response = await authenticatedFetch("/me");
        if (response.ok) {
          const userData = await response.json();
          setUser({
            email: userData.email,
            name: userData.name || `${userData.first_name} ${userData.last_name}`.trim() || session.user.name || "User",
            first_name: userData.first_name,
            last_name: userData.last_name,
            fireflies_api_key: userData.fireflies_api_key,
            zoom_jwt: userData.zoom_jwt,
            phone: userData.phone,
            address: userData.address,
          });
        } else {
          console.error('Failed to fetch user from backend:', response.status);
          // Use session data as fallback
          setUser({
            email: session.user.email || "",
            name: session.user.name || "User",
          });
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
        // Use session data as fallback
        setUser({
          email: session.user.email || "",
          name: session.user.name || "User",
        });
      }
    }
    
    fetchUser();
  }, [session, status]);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError("");
      try {
        // Fetch meetings
        const meetingsRes = await authenticatedFetch("/meetings");
        if (!meetingsRes.ok) throw new Error("Failed to fetch meetings");
        const meetingsData = await meetingsRes.json();
        const meetings = meetingsData.meetings || [];

        // Fetch Google Calendar events
        let calendarEvents: any[] = [];
        try {
          const calRes = await authenticatedFetch("/calendar/events");
          if (calRes.status === 401) {
            console.log("Logging out for 401")
            await authenticatedFetch('/logout', { method: 'POST' });
            localStorage.clear();
            sessionStorage.clear();
            window.location.href = "/login";
            return;
          }
          if (!calRes.ok) throw new Error("Failed to fetch calendar events");
          const calData = await calRes.json();
          calendarEvents = calData.events || [];
        } catch (err) {
          setError("Could not load Google Calendar events.");
        }

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
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard data.");
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
    setSyncingCalendar(true);
    setSyncError("");
    try {
      const res = await authenticatedFetch("/calendar/events");
      if (res.status === 401) {
        await authenticatedFetch('/logout', { method: 'POST' });
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = "/login";
        return;
      }
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
      triggerSync(); // Notify global sync
    } catch (err: any) {
      setSyncError(err.message || "Sync failed");
      setShowReconnect(false);
    } finally {
      setSyncingCalendar(false);
    }
  }

  async function refetchMeetings(background = false) {
    if (!background) setLoading(true); else setRefreshing(true);
    try {
      const meetingsRes = await authenticatedFetch("/meetings");
      const meetingsData = await meetingsRes.json();
      const meetings = meetingsData.meetings || [];
      // Recent activity
      const recent = meetings
        .sort((a: any, b: any) => new Date(b.date).getTime() - new Date(a.date).getTime())
        .slice(0, 5)
        .map((m: any) => ({ id: m.id, type: "Meeting", title: m.title, date: m.date, status: "Completed" }));
      setRecentActivity(recent);
      // Stats
      const total = meetings.length;
      const weekStart = new Date();
      weekStart.setDate(weekStart.getDate() - weekStart.getDay());
      const now = new Date();
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
      const week = meetings.filter((m: any) => new Date(m.date) >= weekStart).length;
      const month = meetings.filter((m: any) => new Date(m.date) >= monthStart).length;
      const byType: Record<string, number> = {};
      meetings.forEach((m: any) => { byType[m.source] = (byType[m.source] || 0) + 1; });
      setMeetingStats({ total, week, month, byType });
    } catch (err) {
      // Keep prior UI; optionally surface subtle error
    } finally {
      if (!background) setLoading(false); else setRefreshing(false);
    }
  }

  async function handleSyncMeetings() {
    setSyncingMeetings(true);
    setSyncError("");
    setRefreshing(true); // show inline updating message immediately when sync starts

    const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
    const waitForVisible = async () => {
      if (typeof document === 'undefined') return;
      while (document.hidden) await sleep(1000);
    };

    try {
      const res = await fetch("/api/external-meetings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "fireflies" }),
      });
      const data = await res.json();
      if (data.error && data.error.includes("Fireflies API key not found")) {
        setSyncError("Fireflies API key not found");
        setSyncingMeetings(false);
        setRefreshing(false);
        return;
      }
      if (!data.task_id) {
        setSyncError("No sync task started. Raw response: " + JSON.stringify(data));
        setSyncingMeetings(false);
        setRefreshing(false);
        return;
      }

      await sleep(1500);

      let status = "PENDING" as string;
      let pollCount = 0;
      let delayMs = 2000;
      const maxDelayMs = 8000;
      const maxPolls = 40;
      const startAt = Date.now();
      const maxTotalMs = 2 * 60 * 1000;

      while (status !== "SUCCESS" && status !== "FAILURE" && pollCount < maxPolls && (Date.now() - startAt) < maxTotalMs) {
        await waitForVisible();
        const jitter = 0.8 + Math.random() * 0.4;
        await sleep(Math.floor(delayMs * jitter));
        try {
          const statusRes = await authenticatedFetch(`/sync/status/${data.task_id}?_=${Date.now()}_${Math.random()}`);
          const statusData = await statusRes.json();
          status = statusData.status;
        } catch {}
        pollCount++;
        delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.5));
        if (status === "FAILURE") {
          setSyncError("Sync failed. Please try again.");
          setSyncingMeetings(false);
          setRefreshing(false);
          return;
        }
      }

      if (status !== "SUCCESS") {
        setSyncError("Sync timed out. Please try again.");
        setSyncingMeetings(false);
        setRefreshing(false);
        return;
      }

      await refetchMeetings(true);
      triggerSync();

      setToast({ message: 'Sync complete. Meetings updated.', type: 'success' });
      setTimeout(() => setToast(null), 3500);
    } catch (err: any) {
      setSyncError("Sync failed: " + (err?.message || err));
    } finally {
      setSyncingMeetings(false);
      setRefreshing(false);
    }
  }

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

  // Add at the top, after imports
  const Tooltip = ({ text, children }: { text: string, children: React.ReactNode }) => {
    const [show, setShow] = useState(false);
    return (
      <span className="relative inline-block"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
        tabIndex={0}
      >
        {children}
        {show && (
          <span className="absolute z-10 left-1/2 -translate-x-1/2 mt-2 px-3 py-1 rounded bg-gray-800 text-white text-xs whitespace-nowrap shadow-lg">
            {text}
          </span>
        )}
      </span>
    );
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      {/* Floating toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded shadow-lg border ${toast.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
          {toast.message}
        </div>
      )}

      {/* Loading and error states */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <span className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-2"></span>
          <span className="text-gray-500">Loading dashboard...</span>
        </div>
      )}
      {error && !loading && (
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-4">{error}</div>
      )}

      {!loading && !error && (
        <>
          <h2 className="text-2xl font-bold mb-6 text-blue-700">Dashboard</h2>
          <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-4xl flex flex-col gap-8 border border-gray-100">
            {/* Quick Actions */}
            <div className="flex flex-col gap-2 mb-6">
              <div className="flex gap-4">
                {session?.user?.plan === 'pro' ? (
                  <Link href="/upload">
                    <button
                      className="px-4 py-2 rounded bg-blue-600 text-white font-semibold transition hover:bg-blue-700 flex items-center"
                      aria-label="Upload Audio (Pro feature)"
                      title="Pro feature"
                    >
                      <span className="mr-2" aria-hidden>🔒</span>
                      <span>Upload Audio</span>
                      <span className="ml-2 text-[10px] uppercase tracking-wide bg-yellow-200 text-yellow-800 rounded px-1 py-0.5">Pro</span>
                    </button>
                  </Link>
                ) : (
                  <button
                    className="px-4 py-2 rounded bg-blue-600 text-white font-semibold transition hover:bg-blue-700 flex items-center opacity-90"
                    aria-label="Upload Audio (Pro feature)"
                    title="Upgrade to Pro to upload audio"
                    onClick={() => {
                      router.push('/upload');
                    }}
                  >
                    <span className="mr-2" aria-hidden>🔒</span>
                    <span>Upload Audio</span>
                    <span className="ml-2 text-[10px] uppercase tracking-wide bg-yellow-200 text-yellow-800 rounded px-1 py-0.5">Pro</span>
                  </button>
                )}

                <button className="px-4 py-2 rounded bg-green-600 text-white font-semibold transition hover:bg-green-700" onClick={handleSyncCalendar} disabled={syncingCalendar}>
                  {syncingCalendar ? "Syncing..." : "Sync Google Calendar"}
                </button>
                <button className="px-4 py-2 rounded bg-purple-600 text-white font-semibold transition hover:bg-purple-700" onClick={handleSyncMeetings} disabled={syncingMeetings}>
                  {syncingMeetings ? "Syncing..." : "Sync Transcribed Meetings (Fireflies/Zoom)"}
                </button>
                {showReconnect && (
                  <button className="px-4 py-2 rounded bg-red-600 text-white font-semibold transition hover:bg-red-700" onClick={handleReconnectGoogle}>
                    Reconnect Google
                  </button>
                )}
              </div>
              {refreshing && <div className="text-xs text-gray-500">Updating dashboard data…</div>}
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
                      <span className="font-medium text-gray-800 flex-1">{m.title}</span>
                      <span className="text-gray-500 text-sm flex-1 text-center">{formatDate(m.date)}</span>
                      <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs ml-2 text-center">{m.source}</span>
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
                      <span className="text-gray-500 text-sm flex-1 text-center">{formatDate(a.date)}</span>
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
              <div className="bg-green-50 rounded-lg p-4 flex flex-col items-center border border-green-200">
                <span className="text-3xl font-bold text-green-700">{meetingStats.total}</span>
                <span className="text-gray-700 flex items-center gap-1">
                  Total Completed Meetings
                  <Tooltip text="All meetings completed">
                    <span className="ml-1 cursor-pointer" aria-label="info">🛈</span>
                  </Tooltip>
                </span>
              </div>
              <div className="bg-green-50 rounded-lg p-4 flex flex-col items-center border border-green-200">
                <span className="text-xl font-bold text-green-700">{meetingStats.week}</span>
                <span className="text-gray-700 flex items-center gap-1">
                  Completed this Week
                  <Tooltip text="Meetings with a date earlier than now, this week only">
                    <span className="ml-1 cursor-pointer" aria-label="info">🛈</span>
                  </Tooltip>
                </span>
                <span className="text-xl font-bold text-green-700 mt-2">{meetingStats.month}</span>
                <span className="text-gray-700 flex items-center gap-1">
                  Completed this Month
                  <Tooltip text="Meetings with a date earlier than now, this month only">
                    <span className="ml-1 cursor-pointer" aria-label="info">🛈</span>
                  </Tooltip>
                </span>
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
        </>
      )}
    </main>
  );
}

export default Dashboard;