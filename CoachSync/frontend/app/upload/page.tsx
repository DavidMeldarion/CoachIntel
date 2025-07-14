"use client";

import React, { useState } from 'react';
import { uploadAudio } from '../../lib/api';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setStatus('Uploading...');
    try {
      const res = await uploadAudio(file);
      setStatus(`Uploaded: ${res.filename}`);
    } catch (err) {
      setStatus('Upload failed');
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Upload Audio</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="font-semibold">Audio File (.mp3, .m4a)</label>
          <input
            type="file"
            accept="audio/*"
            className="border rounded p-2"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          <button type="submit" className="btn-primary">Upload</button>
          {status && <div className="mt-2 text-sm">{status}</div>}
        </form>
        <div className="text-gray-700 text-center">Upload form coming soon.</div>
      </div>
    </main>
  );
}