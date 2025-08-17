"use client";

import { useState } from "react";
import Link from "next/link";

export default function WaitlistPage() {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [smsOptIn, setSmsOptIn] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const url = new URL(window.location.href);
      const payload: any = {
        email,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        source: 'landing',
        utm_source: url.searchParams.get('utm_source') || undefined,
        utm_medium: url.searchParams.get('utm_medium') || undefined,
        utm_campaign: url.searchParams.get('utm_campaign') || undefined,
        consent_email: true,
        consent_sms: false,
      };
      if (phone && smsOptIn) {
        payload.phone = phone;
        payload.consent_sms = true;
      }
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || "Failed to join waitlist");
      setSuccess("You're on the list!");
      setEmail("");
      setFirstName("");
      setLastName("");
      setPhone("");
      setSmsOptIn(false);
    } catch (err: any) {
      setError(err?.message || "Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-lg mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h1 className="text-2xl font-bold text-blue-700 mb-2">Join the Waitlist</h1>
        <p className="text-gray-600 mb-6">Enter your details to get early access when we open the doors.</p>

        {success && <div className="mb-4 px-4 py-2 bg-green-50 text-green-700 border border-green-200 rounded">{success}</div>}
        {error && <div className="mb-4 px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded">{error}</div>}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">First name (optional)</label>
              <input id="firstName" value={firstName} onChange={(e)=>setFirstName(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">Last name (optional)</label>
              <input id="lastName" value={lastName} onChange={(e)=>setLastName(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">Phone (optional)</label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="(555) 555-5555"
            />
            <label className="mt-2 inline-flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={smsOptIn} onChange={(e)=>setSmsOptIn(e.target.checked)} />
              I agree to receive SMS updates about my account.
            </label>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className={`w-full rounded bg-blue-600 text-white font-semibold px-4 py-2 hover:bg-blue-700 transition ${submitting ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {submitting ? 'Submitting…' : 'Join Waitlist'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link href="/login" className="text-blue-600 hover:underline">Already have an account? Sign in</Link>
        </div>
      </div>
    </main>
  );
}
