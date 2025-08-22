"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function BillingPage() {
  const searchParams = useSearchParams();
  const selected = searchParams.get("selected");
  const planLabel = selected === 'pro' ? 'Pro' : selected === 'plus' ? 'Plus' : null;
  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h1 className="text-2xl font-bold text-blue-700 mb-2">Complete your subscription</h1>
        {planLabel && (
          <p className="text-sm text-gray-700 mb-2">Selected plan: <span className="font-semibold">{planLabel}</span></p>
        )}
        <p className="text-gray-600 mb-4">
          Billing integration is coming soon. Your account will not be upgraded until payment is completed.
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-6">
          <li>We will redirect you to the payment provider when available.</li>
          <li>You can continue exploring the app; free features remain available.</li>
        </ul>
  <Link href="/dashboard" className="inline-flex items-center rounded bg-blue-600 text-white px-4 py-2 font-semibold hover:bg-blue-700">
          Go to Dashboard
        </Link>
      </div>
    </main>
  );
}
