"use client";
import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';

async function fetcher(url: string) {
  const r = await fetch(url, { credentials: 'include' });
  if (!r.ok) throw new Error('Failed');
  return r.json();
}

type OrgAdminUser = { id: number; email: string; first_name: string; last_name: string };

type Me = { email: string; org_id?: number | null; site_admin?: boolean; org_admin_ids?: number[] };

export default function OrgAdminsPage() {
  const { data: me } = useSWR<Me>('/api/user', fetcher);
  const [orgIdInput, setOrgIdInput] = useState<number | null>(null);

  const effectiveOrgId = useMemo(() => {
    if (!me) return null;
    if (me.site_admin && orgIdInput) return orgIdInput;
    return me.org_id ?? null;
  }, [me, orgIdInput]);

  const { data: admins, mutate, isLoading } = useSWR<OrgAdminUser[]>(
    () => (effectiveOrgId ? `/api/orgs/${effectiveOrgId}/admins` : null),
    fetcher
  );

  const [email, setEmail] = useState('');
  // Invite creation moved to Leads page

  async function addAdmin() {
    if (!effectiveOrgId || !email) return;
    await fetch(`/api/orgs/${effectiveOrgId}/admins`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ user_email: email.trim() }),
    });
    setEmail('');
    mutate();
  }

  async function removeAdmin(id: number) {
    if (!effectiveOrgId) return;
    await fetch(`/api/orgs/${effectiveOrgId}/admins/${id}`, { method: 'DELETE', credentials: 'include' });
    mutate();
  }

  // createInvite removed

  return (
    <div className="px-6">
      {/* Admin tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex gap-6" aria-label="Tabs">
          <Link href="/admin/leads" className="border-b-2 border-transparent px-1 pb-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">Leads</Link>
          <Link href="/admin/org-admins" className="border-b-2 border-blue-600 px-1 pb-2 text-sm font-medium text-blue-600">Org Admins</Link>
        </nav>
      </div>

      <h1 className="text-xl font-semibold mb-4">Organization Admins</h1>

      {me?.site_admin && (
        <div className="mb-4 flex items-center gap-2">
          <label className="text-sm text-gray-600">Org ID:</label>
          <input type="number" value={orgIdInput ?? ''} onChange={(e) => setOrgIdInput(parseInt(e.target.value) || 0)} className="border rounded px-2 py-1 w-32" placeholder="e.g. 1" />
          <span className="text-xs text-gray-500">As site admin, you can manage any org by ID.</span>
        </div>
      )}

      <div className="mb-4 flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="admin@email.com"
          className="border rounded px-3 py-2 w-80"
        />
  <button onClick={addAdmin} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Add Admin</button>
      </div>

  {/* Invite creation moved to Leads page */}

      <div className="bg-white shadow rounded overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {(admins ?? []).length === 0 && (
              <tr><td colSpan={2} className="px-3 py-6 text-center text-gray-500">No admins yet.</td></tr>
            )}
            {(admins ?? []).map(a => (
              <tr key={a.id} className="border-t">
                <td className="px-3 py-2 text-sm">
                  <div className="font-medium">{a.email}</div>
                  <div className="text-gray-500">{[a.first_name, a.last_name].filter(Boolean).join(' ')}</div>
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => removeAdmin(a.id)} className="text-red-600 hover:underline">Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
