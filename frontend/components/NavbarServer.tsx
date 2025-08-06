import Link from "next/link";
import { getUser } from "../lib/dal";
import LogoutButton from "./LogoutButton";
import UserDropdown from "./UserDropdown";

export default async function Navbar() {
  const user = await getUser();

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="text-xl font-bold text-blue-700">
              CoachIntel
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <div className="hidden md:flex items-center space-x-8">
                  <Link 
                    href="/dashboard" 
                    className="text-gray-700 hover:text-blue-700 font-medium"
                  >
                    Dashboard
                  </Link>
                  <Link 
                    href="/timeline" 
                    className="text-gray-700 hover:text-blue-700 font-medium"
                  >
                    Timeline
                  </Link>
                  <Link 
                    href="/upload" 
                    className="text-gray-700 hover:text-blue-700 font-medium"
                  >
                    Upload
                  </Link>
                  <Link 
                    href="/profile" 
                    className="text-gray-700 hover:text-blue-700 font-medium"
                  >
                    Profile
                  </Link>
                  <Link 
                    href="/apikeys" 
                    className="text-gray-700 hover:text-blue-700 font-medium"
                  >
                    API Keys
                  </Link>
                </div>

                <UserDropdown user={user} />
              </>
            ) : (
              <div className="flex items-center space-x-4">
                <Link 
                  href="/login" 
                  className="text-gray-700 hover:text-blue-700 font-medium"
                >
                  Login
                </Link>
                <Link 
                  href="/signup" 
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
