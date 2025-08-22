"use client";

import React, { useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

const plans = [
	{
		id: "free",
		name: "Free Tier",
		price: "$0",
		description: "Sync your meetings and calendar. No AI summaries.",
		features: [
			"Connect Fireflies/Zoom",
			"Sync meetings & calendar",
			"View timeline",
			"No summaries",
		],
	},
	{
		id: "plus",
		name: "Plus",
		price: "$9/mo",
		description: "Everything except uploading your own audio.",
		features: [
			"All Free features",
			"AI summaries for synced meetings",
			"Insights & action items",
			"No manual audio uploads",
		],
	},
	{
		id: "pro",
		name: "Pro",
		price: "$19/mo",
		description: "Full access to all features.",
		features: [
			"All Plus features",
			"Upload and transcribe your own audio",
			"Priority processing",
		],
	},
] as const;

export default function PurchasePage() {
	const { status, data: session, update } = useSession();
	const router = useRouter();
	const searchParams = useSearchParams();
	const [submitting, setSubmitting] = useState<string | null>(null);
	const [error, setError] = useState("");

	const qp = (searchParams.get("current") || "").toLowerCase();
	const currentFromQuery = ["free", "plus", "pro"].includes(qp)
		? (qp as "free" | "plus" | "pro")
		: undefined;
	const currentPlan =
		currentFromQuery || ((session as any)?.user?.plan as "free" | "plus" | "pro" | undefined);

	const hqp = (searchParams.get("highlight") || "").toLowerCase();
	const highlightFromQuery = ["free", "plus", "pro"].includes(hqp)
		? (hqp as "free" | "plus" | "pro")
		: undefined;

	const notice = searchParams.get("notice") || undefined;

	const selectPlan = async (plan: "free" | "plus" | "pro") => {
		setError("");
		setSubmitting(plan);
		try {
			// Only allow immediate persistence for the free plan.
			if (plan === "free") {
				// Call our Next proxy which forwards cookies and email
				const apiBase = process.env.NEXT_PUBLIC_API_URL;
				const res = await fetch(`${apiBase}/user`, {
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ plan }),
					credentials: "include",
				});
				if (!res.ok) {
					const data = await res.json().catch(() => ({}));
					throw new Error(data?.detail || data?.error || "Failed to set plan");
				}

				// Revalidate session to pull in updated plan
				try { await update(); } catch {}

				// Redirect to dashboard for free tier
				router.replace("/dashboard");
			} else {
				// For paid plans (plus/pro), do NOT assign the plan yet.
				// Redirect user to billing to complete purchase.
				router.replace(`/billing?selected=${plan}`);
			}
		} catch (e: any) {
			setError(e?.message || String(e));
		} finally {
			setSubmitting(null);
		}
	};

	return (
		<main className="min-h-screen bg-gray-50 p-6">
			<div className="max-w-5xl mx-auto">
				<h1 className="text-3xl font-bold text-blue-700 mb-2">Choose your plan</h1>
				<p className="text-gray-600 mb-4">Upgrade anytime. Plans billed through your app store/provider coming soon.</p>

				{notice === 'upload-pro-required' && (
					<div className="mb-6 flex items-start gap-3 rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-900">
						<svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l6.518 11.59c.75 1.335-.213 3.011-1.742 3.011H3.48c-1.53 0-2.493-1.676-1.743-3.01L8.257 3.1zM11 14a1 1 0 10-2 0 1 1 0 002 0zm-1-2a1 1 0 01-1-1V8a1 1 0 112 0v3a1 1 0 01-1 1z" clipRule="evenodd"/></svg>
						<div>
							<p className="font-medium">Upload Audio is a Pro feature.</p>
							<p>To upload and transcribe your own audio, please upgrade to the Pro plan below.</p>
						</div>
					</div>
				)}

				{error && (
					<div className="mb-4 px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded">{error}</div>
				)}
				<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
					{plans.map((p) => {
						const isCurrent = currentPlan === p.id;
						const isHighlighted = highlightFromQuery === p.id;
						const isUploadRequiredBadge = notice === 'upload-pro-required' && p.id === 'pro';
						return (
							<div
								key={p.id}
								id={`plan-${p.id}`}
								className={`bg-white rounded-xl border ${
									isCurrent
										? "border-blue-500 ring-2 ring-blue-200"
										: isHighlighted
										? "border-purple-500 ring-2 ring-purple-200"
										: "border-gray-200"
								} shadow-sm p-6 flex flex-col`}
								title={isUploadRequiredBadge ? 'Required for Upload Audio' : undefined}
							>
								<div className="flex items-center justify-between">
									<h2 className="text-xl font-semibold text-gray-900">{p.name}</h2>
									{isCurrent ? (
										<span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">Your plan</span>
									) : isUploadRequiredBadge ? (
										<span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">Required for Upload</span>
									) : (
										p.id === "pro" && (
											<span className="text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded">Best value</span>
										)
									)}
								</div>
								<div className="mt-2 text-2xl font-bold text-gray-900">{p.price}</div>
								<p className="mt-1 text-gray-600">{p.description}</p>
								<ul className="mt-4 space-y-2 text-sm text-gray-700 list-disc list-inside">
									{p.features.map((f) => (
										<li key={f}>{f}</li>
									))}
								</ul>
								<button
									className={`mt-6 inline-flex items-center justify-center rounded px-4 py-2 font-semibold text-white transition ${
										isCurrent
											? "bg-gray-300 cursor-not-allowed"
											: p.id === "free"
											? "bg-gray-600 hover:bg-gray-700"
											: p.id === "plus"
											? "bg-purple-600 hover:bg-purple-700"
											: "bg-blue-600 hover:bg-blue-700"
									} ${submitting === p.id ? "opacity-70 cursor-not-allowed" : ""}`}
									onClick={() => !isCurrent && selectPlan(p.id)}
									disabled={!!submitting || isCurrent}
								>
									{isCurrent
										? "Current plan"
										: submitting === p.id
										? "Setting up..."
										: p.id === "free"
										? "Choose Free"
										: p.id === "plus"
										? "Choose Plus"
										: "Choose Pro"}
								</button>
							</div>
						);
					})}
				</div>
			</div>
		</main>
	);
}
