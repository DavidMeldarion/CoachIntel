import React from 'react';

export default function Dashboard() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <p className="mb-6">Welcome, Coach! Here you can manage your clients and view recent sessions.</p>
      <div className="w-full max-w-md bg-white rounded shadow p-6">
        <h3 className="font-semibold mb-2">Recent Clients</h3>
        <ul className="list-disc ml-6 text-gray-700">
          <li>Jane Doe</li>
          <li>John Smith</li>
        </ul>
      </div>
    </main>
  );
}