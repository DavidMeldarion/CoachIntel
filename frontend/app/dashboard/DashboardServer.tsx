import React from 'react';
import Link from 'next/link';
import { getUser, verifySession } from "../../lib/dal";
import { getApiUrl } from "../../lib/apiUrl";

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

      {/* Dashboard Content */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* Meeting Stats Cards */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Meetings</h3>
          <p className="text-3xl font-bold text-blue-600">{meetingStats.total}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">This Week</h3>
          <p className="text-3xl font-bold text-green-600">{meetingStats.week}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">This Month</h3>
          <p className="text-3xl font-bold text-purple-600">{meetingStats.month}</p>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Upcoming Meetings</h3>
          {upcomingMeetings.length > 0 ? (
            <div className="space-y-3">
              {upcomingMeetings.map((meeting: any, index: number) => (
                <div key={index} className="flex justify-between items-center py-2 border-b last:border-b-0">
                  <div>
                    <p className="font-medium">{meeting.title || 'Untitled Meeting'}</p>
                    <p className="text-sm text-gray-600">{new Date(meeting.date).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No upcoming meetings</p>
          )}
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
          {recentActivity.length > 0 ? (
            <div className="space-y-3">
              {recentActivity.map((activity: any, index: number) => (
                <div key={index} className="flex justify-between items-center py-2 border-b last:border-b-0">
                  <div>
                    <p className="font-medium">{activity.title || 'Meeting'}</p>
                    <p className="text-sm text-gray-600">{new Date(activity.date).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No recent activity</p>
          )}
        </div>
      </div>
    </main>
  );
}
