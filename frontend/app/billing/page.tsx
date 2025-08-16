"use client";

import Link from "next/link";

export default function BillingPage() {
  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h1 className="text-2xl font-bold text-blue-700 mb-2">Complete your subscription</h1>
        <p className="text-gray-600 mb-4">
          Thank you for choosing a paid plan. Billing integration is coming soon.
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-6">
          <li>We will redirect you to the payment provider when available.</li>
          <li>Your selection has been saved; you can continue exploring the app.</li>
        </ul>
        <Link href="/dashboard" className="inline-flex items-center rounded bg-blue-600 text-white px-4 py-2 font-semibold hover:bg-blue-700">
          Go to Dashboard
        </Link>
      </div>
    </main>
  );
}
