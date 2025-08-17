import Link from "next/link";
import { Suspense } from "react";
import GoogleLoginButton from "../../components/GoogleLoginButton";
import { AuthErrorBoundary } from "../../components/ErrorBoundary";
import { LoadingOverlay } from "../../components/LoadingStates";
import { useSearchParams } from "next/navigation";

function SignupPageContent() {
  const searchParams = useSearchParams();
  const access = searchParams.get('access');
  const allowed = !!access && access.length >= 8; // placeholder access code check

  if (!allowed) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md border border-gray-100 text-center">
          <h2 className="text-2xl font-bold mb-4 text-blue-700">Signup by Invitation Only</h2>
          <p className="text-gray-600 mb-6">We're currently onboarding users from our waitlist. Please join the waitlist to request early access.</p>
          <Link href="/waitlist" className="inline-flex items-center rounded bg-blue-600 text-white px-4 py-2 font-semibold hover:bg-blue-700">Join Waitlist</Link>
        </div>
      </main>
    );
  }

  return (
    <AuthErrorBoundary>
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <h2 className="text-2xl font-bold mb-6 text-blue-700">Create Your CoachIntel Account</h2>
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
          {/* Google OAuth Signup */}
          <GoogleLoginButton />
          
          <Link
            href="/login"
            className="text-blue-600 hover:underline mt-2 text-center"
          >
            Already have an account? Sign in
          </Link>
        </div>
      </main>
    </AuthErrorBoundary>
  );
}

export default function Signup() {
  return (
    <Suspense fallback={<LoadingOverlay message="Loading signup page..." /> }>
      <SignupPageContent />
    </Suspense>
  );
}
