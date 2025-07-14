import React from 'react';

export default function Dashboard() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Dashboard</h2>
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-2xl flex flex-col gap-6 border border-gray-100">
        {/* Add your dashboard content here, styled similarly */}
        <div className="text-gray-700 text-center">Welcome to your dashboard!</div>
      </div>
    </main>
  );
}