import { getUser, verifySession } from "../lib/dal";
import { cookies } from 'next/headers';

export default async function DebugAuth() {
  try {
    // Check session cookie
    const sessionCookie = (await cookies()).get('session')?.value;
    const allCookies = (await cookies()).toString();
    
    // Check session verification
    const session = await verifySession();
    
    // Check user data
    const user = await getUser();
    
    return (
      <div className="bg-red-100 border border-red-300 p-4 mb-4 text-xs">
        <h3 className="font-bold text-red-800">Debug Auth State:</h3>
        <div className="mt-2 space-y-1">
          <div><strong>Session Cookie:</strong> {sessionCookie ? 'EXISTS' : 'MISSING'}</div>
          <div><strong>Session Cookie Preview:</strong> {sessionCookie ? sessionCookie.substring(0, 30) + '...' : 'none'}</div>
          <div><strong>All Cookies:</strong> {allCookies || 'none'}</div>
          <div><strong>Session Verified:</strong> {session ? 'YES' : 'NO'}</div>
          <div><strong>Session Data:</strong> {session ? JSON.stringify(session) : 'null'}</div>
          <div><strong>User Data:</strong> {user ? JSON.stringify(user) : 'null'}</div>
        </div>
      </div>
    );
  } catch (error) {
    return (
      <div className="bg-red-100 border border-red-300 p-4 mb-4 text-xs">
        <h3 className="font-bold text-red-800">Debug Auth Error:</h3>
        <div className="mt-2">
          <strong>Error:</strong> {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }
}
