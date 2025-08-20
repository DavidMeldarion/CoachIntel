"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { CONSENT_VERSION } from "../../lib/consent";
import { useSession } from "next-auth/react";

export default function WaitlistPage() {
  const { data: session, status } = useSession();
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [smsOptIn, setSmsOptIn] = useState(false);
  const [emailOptIn, setEmailOptIn] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // When authenticated, show friendly banner and hide form submission errors
  useEffect(() => {
    if (status === 'authenticated') {
      setError(null);
      setSuccess(null);
    }
  }, [status]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      // If user is logged in, short-circuit with friendly message
      if (status === 'authenticated') {
        setError("You're already signed in—no need to join the waitlist. Head to your dashboard.");
        return;
      }
      const url = new URL(window.location.href);
      const payload: any = {
        email,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        source: 'landing',
        utm_source: url.searchParams.get('utm_source') || undefined,
        utm_medium: url.searchParams.get('utm_medium') || undefined,
        utm_campaign: url.searchParams.get('utm_campaign') || undefined,
        // explicit consent flags from checkboxes
        consent_email: emailOptIn,
        consent_sms: smsOptIn,
        consent_version: CONSENT_VERSION,
      };
      if (phone) {
        payload.phone = phone;
      }
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 409 && (data?.code === 'already_logged_in' || data?.message)) {
        setError(data?.message || "You're already signed in—no need to join the waitlist.");
        return;
      }
      if (!res.ok) throw new Error(data?.detail || data?.error || "Failed to join waitlist");
      setSuccess("You're on the list!");
      setEmail("");
      setFirstName("");
      setLastName("");
      setPhone("");
      setSmsOptIn(false);
  setEmailOptIn(false);
    } catch (err: any) {
      setError(err?.message || "Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="ci-card">
        <div className="sm:flex sm:items-center sm:justify-between">
          <div>
            <h1 className="ci-heading">Get early access</h1>
            <p className="ci-subheading">Join the waitlist — we'll email you when your invite is ready.</p>
          </div>
        </div>

        {status === 'authenticated' && (
          <div className="mt-6 mb-4 px-4 py-3 bg-blue-50 text-blue-800 border border-blue-200 rounded">
            You're signed in as <span className="font-medium">{session?.user?.email || session?.user?.name || 'your account'}</span>. You don't need to join the waitlist.
            <div className="mt-2">
              <Link href="/dashboard" className="text-blue-700 underline">Go to your dashboard</Link>
            </div>
          </div>
        )}

        {success && <div className="mt-6 mb-4 px-4 py-2 bg-green-50 text-green-700 border border-green-200 rounded">{success}</div>}
        {error && <div className="mt-6 mb-4 px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded">{error}</div>}

  <form onSubmit={onSubmit} className="ci-form" aria-disabled={status === 'authenticated'}>
          <div>
            <label htmlFor="email" className="sr-only">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={status === 'authenticated'}
              className={`ci-input ${status === 'authenticated' ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              placeholder="you@example.com"
            />
          </div>

          <div className="ci-form-grid">
            <div>
              <label htmlFor="firstName" className="sr-only">First name</label>
              <input id="firstName" value={firstName} onChange={(e)=>setFirstName(e.target.value)} disabled={status === 'authenticated'} className={`ci-input ${status === 'authenticated' ? 'bg-gray-100 cursor-not-allowed' : ''}`} placeholder="First name (optional)" />
            </div>
            <div>
              <label htmlFor="lastName" className="sr-only">Last name</label>
              <input id="lastName" value={lastName} onChange={(e)=>setLastName(e.target.value)} disabled={status === 'authenticated'} className={`ci-input ${status === 'authenticated' ? 'bg-gray-100 cursor-not-allowed' : ''}`} placeholder="Last name (optional)" />
            </div>
          </div>

          <div>
            <label htmlFor="phone" className="sr-only">Phone</label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={status === 'authenticated'}
              className={`ci-input ${status === 'authenticated' ? 'bg-gray-100 cursor-not-allowed' : ''}`}
              placeholder="Phone (optional)"
            />
          </div>

          <div className="ci-checkbox-row pt-1">
            <div className="flex items-center">
              <input id="emailOptIn" type="checkbox" checked={emailOptIn} onChange={(e)=>setEmailOptIn(e.target.checked)} disabled={status === 'authenticated'} className="ci-checkbox" />
            </div>
            <div className="ci-field-text">
              <label htmlFor="emailOptIn" className="font-medium">Email updates</label>
              <div className="ci-helper">Occasional product news & account messages. <a href="/privacy" className="underline">Privacy</a></div>
            </div>
          </div>

          <div className="ci-checkbox-row">
            <div className="flex items-center">
              <input id="smsOptIn" type="checkbox" checked={smsOptIn} onChange={(e)=>setSmsOptIn(e.target.checked)} disabled={status === 'authenticated'} className="ci-checkbox" />
            </div>
            <div className="ci-field-text">
              <label htmlFor="smsOptIn" className="font-medium">SMS updates</label>
              <div className="ci-helper">Msg/data rates may apply. Reply HELP for help, STOP to unsubscribe.</div>
            </div>
          </div>

          <input type="hidden" name="consent_version" value={CONSENT_VERSION} />

          <button type="submit" disabled={submitting || status === 'authenticated'} className={`ci-btn-primary ${(submitting || status === 'authenticated') ? 'opacity-70 cursor-not-allowed' : ''}`}>
            {status === 'authenticated' ? 'Signed in — Waitlist disabled' : (submitting ? 'Submitting…' : 'Request access')}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-500">
          {status === 'authenticated' ? (
            <Link href="/dashboard" className="text-sky-600 hover:underline">Go to your dashboard</Link>
          ) : (
            <Link href="/login" className="text-sky-600 hover:underline">Already have an account? Sign in</Link>
          )}
        </div>
      </div>
    </main>
  );
}
