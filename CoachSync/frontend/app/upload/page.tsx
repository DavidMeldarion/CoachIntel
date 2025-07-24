"use client";

import React, { useState } from 'react';
import { uploadAudio } from '../../lib/api';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please select an audio file.");
      return;
    }
    setIsUploading(true);
    setStatus("");
    setError("");
    try {
      const res = await uploadAudio(file);
      setStatus(`Uploaded: ${res.filename}`);
      setFile(null);
    } catch (err) {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  if (isUploading) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p className="text-gray-600">Uploading...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
        <h2 className="text-2xl font-bold mb-4 text-blue-700 text-center">Upload Audio</h2>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label htmlFor="audio-upload" className="font-semibold text-gray-700">Audio File (.mp3, .m4a)</label>
          <input
            id="audio-upload"
            type="file"
            accept="audio/*"
            className="border rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
            onChange={e => setFile(e.target.files?.[0] || null)}
            disabled={isUploading}
          />
          <button
            type="submit"
            className={`px-4 py-2 rounded bg-blue-600 text-white font-semibold transition hover:bg-blue-700 ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={isUploading}
          >
            {isUploading ? "Uploading..." : "Upload"}
          </button>
          {error && <div className="mt-2 text-sm text-center text-red-600">{error}</div>}
          {status && !error && <div className="mt-2 text-sm text-center text-green-700">{status}</div>}
        </form>
        <div className="text-gray-500 text-center text-sm mt-2">Supported formats: .mp3, .m4a. Max size 100MB.</div>
      </div>
    </main>
  );
}