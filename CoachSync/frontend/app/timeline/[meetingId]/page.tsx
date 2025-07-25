"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function MeetingTranscriptPage({ params }: { params: { meetingId: string } }) {
  const meetingId = params.meetingId;
  const [meeting, setMeeting] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    async function fetchMeeting() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`/api/meetings/${encodeURIComponent(meetingId)}`);
        if (!res.ok) throw new Error("Failed to fetch meeting");
        const data = await res.json();
        setMeeting(data);
      } catch (err: any) {
        setError(err.message || "Error loading meeting");
      } finally {
        setLoading(false);
      }
    }
    fetchMeeting();
  }, [meetingId]);

  if (loading) {
    return <div className="flex items-center justify-center py-8"><span className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-2"></span>Loading transcript...</div>;
  }
  if (error) {
    return <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-4">{error}</div>;
  }
  if (!meeting) {
    return <div className="text-gray-500">Meeting not found.</div>;
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-3xl border border-gray-100">
        <h2 className="text-2xl font-bold mb-4 text-blue-700">{meeting.title || "Meeting Transcript"}</h2>
        <div className="mb-2 text-gray-600">Date: {meeting.date}</div>
        <div className="mb-2 text-gray-600">Client: {meeting.client_name}</div>
        <div className="mb-6 text-gray-600">Duration: {Math.floor(meeting.duration / 60)}m {meeting.duration % 60}s</div>
        <h3 className="text-lg font-semibold mb-2">Full Transcript</h3>
        <div className="whitespace-pre-wrap text-gray-800 bg-gray-50 p-4 rounded border max-h-[500px] overflow-y-auto">
          {meeting.transcript?.full_text || "No transcript available."}
        </div>
      </div>
      <button className="mt-6 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={() => router.back()}>
        Back to Timeline
      </button>
    </main>
  );
}
