import React from 'react';
import Link from 'next/link';
import { getUser, verifySession } from "../../lib/dal";
import { getApiUrl } from "../../lib/apiUrl";
import DashboardClient from './DashboardClient';

async function fetchMeetings() {
  try {
    const response = await fetch(getApiUrl("/meetings"), {
      headers: {
        'Cookie': require('next/headers').cookies().toString(),
      },
      cache: 'no-store',
    });
    if (!response.ok) throw new Error("Failed to fetch meetings");
    const data = await response.json();
    return data.meetings || [];
  } catch (error) {
    console.error('Failed to fetch meetings:', error);
    return [];
  }
}

async function fetchCalendarEvents() {
  try {
    const response = await fetch(getApiUrl("/calendar/events"), {
      headers: {
        'Cookie': require('next/headers').cookies().toString(),
      },
      cache: 'no-store',
    });
    if (!response.ok) throw new Error("Failed to fetch calendar events");
    const data = await response.json();
    return data.events || [];
  } catch (error) {
    console.error('Failed to fetch calendar events:', error);
    return [];
  }
}

export default async function Dashboard() {
  // Verify session and get user
  await verifySession();
  const user = await getUser();

  if (!user) {
    return (
      <main className="p-8">
        <div className="text-center">
          <p className="text-gray-600">Please log in to access the dashboard.</p>
          <Link href="/login" className="text-blue-600 hover:underline">
            Go to Login
          </Link>
        </div>
      </main>
    );
  }

  // Fetch data on the server
  const [meetings, calendarEvents] = await Promise.all([
    fetchMeetings(),
    fetchCalendarEvents(),
  ]);

  // Process data for stats
  const now = new Date();
  const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  const meetingStats = {
    total: meetings.length,
    week: meetings.filter((m: any) => new Date(m.date) > oneWeekAgo).length,
    month: meetings.filter((m: any) => new Date(m.date) > oneMonthAgo).length,
    byType: meetings.reduce((acc: Record<string, number>, m: any) => {
      acc[m.type || 'Unknown'] = (acc[m.type || 'Unknown'] || 0) + 1;
      return acc;
    }, {}),
  };

  const upcomingMeetings = calendarEvents.slice(0, 5);
  const recentActivity = meetings
    .sort((a: any, b: any) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 10);

  return (
    <main className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user.first_name || user.name || 'Coach'}!
        </h1>
        <p className="text-gray-600 mt-2">
          Here's what's happening with your coaching sessions.
        </p>
      </div>

      {/* Pass data to client component for interactive features */}
      <DashboardClient 
        user={user}
        initialMeetings={meetings}
        initialCalendarEvents={upcomingMeetings}
        initialRecentActivity={recentActivity}
        initialMeetingStats={meetingStats}
      />
    </main>
  );
}
