"use client";
import React, { useEffect, useState, useMemo } from 'react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';

interface ClientItem {
  id: string;
  status: string;
  person_id: string;
  person_name?: string | null;
  last_meeting_at?: string | null;
  last_meeting_summary?: string | null;
  next_meeting_at?: string | null;
  notes?: string | null;
}

interface ClientsApiResponse {
  items: ClientItem[];
  total: number;
}

interface TimelineMeeting {
  id: string;
  started_at?: string;
  ended_at?: string;
  topic?: string;
  transcript_status?: string;
  summary_overview?: string;
}

export default function ClientsPage() {
  const { data: session, status } = useSession();
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(50);
  const [refreshTs, setRefreshTs] = useState<number>(0);

  const authenticated = !!session?.user;

  useEffect(() => {
    if (!authenticated) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        // Fetch base clients
        const headers: Record<string,string> = {};
        if (session?.user?.email) headers['x-user-email'] = session.user.email;
  const res = await fetch(`/api/clients?limit=${pageSize}&offset=${page * pageSize}`, {
          credentials: 'include',
          headers,
        });
        if (!res.ok) throw new Error(`Failed to load clients (${res.status})`);
        const data: ClientsApiResponse = await res.json();
        // For each client fetch its timeline limited to 1 (latest meeting) for summary + compute next meeting
        const enriched: ClientItem[] = [];
        for (const item of data.items) {
          let lastMeetingSummary: string | null = null;
          let nextMeetingAt: string | null = null;
          try {
            const tRes = await fetch(`/api/clients/${item.id}/timeline?limit=5`, { credentials: 'include', headers });
            if (tRes.ok) {
              const tData = await tRes.json();
              // Sort meetings by start desc just in case
              const meetings: TimelineMeeting[] = (tData.items || []).sort((a: any,b: any)=> (b.started_at || '').localeCompare(a.started_at || ''));
              if (meetings.length) {
                const last = meetings[0];
                lastMeetingSummary = last.summary_overview || last.topic || '(No topic)';
              }
              // Next meeting = any future meeting (started_at in future) among first 5 timeline entries
              const nowIso = new Date().toISOString();
              const upcoming = meetings.filter(m => m.started_at && m.started_at > nowIso).sort((a,b)=> (a.started_at||'').localeCompare(b.started_at||''));
              if (upcoming.length) nextMeetingAt = upcoming[0].started_at || null;
            }
          } catch (e:any) {
            console.warn('Timeline load failed for client', item.id, e);
          }
          enriched.push({
            ...item,
            last_meeting_summary: lastMeetingSummary,
            next_meeting_at: nextMeetingAt,
            notes: null,
          });
        }
        if (!cancelled) {
          setClients(enriched);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Failed to load clients');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [authenticated, page, pageSize, refreshTs]);

  const columns = useMemo(() => [
    { key: 'person_name', label: 'Client Name' },
    { key: 'status', label: 'Status' },
    { key: 'last_meeting_at', label: 'Last Meeting' },
    { key: 'last_meeting_summary', label: 'Last Meeting Summary' },
    { key: 'next_meeting_at', label: 'Next Meeting' },
    { key: 'notes', label: 'Notes' },
  ], []);

  if (status === 'loading') {
    return <div className="p-8">Loading session...</div>;
  }
  if (!authenticated) {
    return <div className="p-8">Please log in to view clients.</div>;
  }

  return (
    <div className="px-8 pb-16">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Clients</h1>
        <div className="flex items-center gap-3">
          <button
            className="px-4 py-2 bg-white border border-gray-300 rounded shadow-sm text-sm font-medium hover:bg-gray-50"
            onClick={() => setRefreshTs(Date.now())}
            disabled={loading}
          >Refresh</button>
        </div>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map(col => (
                <th key={col.key} className="px-4 py-3 text-left text-xs font-semibold tracking-wider text-gray-600 uppercase">{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {loading && (
              <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500 text-sm">Loading clients...</td></tr>
            )}
            {!loading && !clients.length && (
              <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500 text-sm">No clients found.</td></tr>
            )}
            {!loading && clients.map(client => (
              <tr key={client.id} className="hover:bg-gray-50 transition">
                <td className="px-4 py-3 text-sm text-gray-700">{client.person_name || `${client.person_id.slice(0,8)}…`}</td>
                <td className="px-4 py-3 text-sm"><span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${client.status === 'active' ? 'bg-green-100 text-green-700' : client.status === 'prospect' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>{client.status}</span></td>
                <td className="px-4 py-3 text-sm text-gray-600">{client.last_meeting_at ? new Date(client.last_meeting_at).toLocaleString() : '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate" title={client.last_meeting_summary || ''}>{client.last_meeting_summary || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{client.next_meeting_at ? new Date(client.next_meeting_at).toLocaleString() : '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-500 italic">{client.notes || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between mt-4">
        <div className="text-sm text-gray-600">Page {page + 1}</div>
        <div className="flex gap-2">
          <button
            disabled={page === 0 || loading}
            onClick={() => setPage(p => Math.max(0, p - 1))}
            className="px-3 py-1.5 rounded border text-sm disabled:opacity-40 bg-white hover:bg-gray-50"
          >Prev</button>
          <button
            disabled={loading || clients.length < pageSize}
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1.5 rounded border text-sm disabled:opacity-40 bg-white hover:bg-gray-50"
          >Next</button>
        </div>
      </div>
      {error && <div className="mt-4 text-sm text-red-600">{error}</div>}
    </div>
  );
}
