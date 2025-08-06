import Link from "next/link";
import { Suspense } from "react";
import SignupForm from "../../components/SignupForm";
import GoogleLoginButton from "../../components/GoogleLoginButton";
import { AuthErrorBoundary } from "../../components/ErrorBoundary";
import { LoadingOverlay } from "../../components/LoadingStates";

function SignupPageContent() {
  return (
    <AuthErrorBoundary>
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <h2 className="text-2xl font-bold mb-6 text-blue-700">Create Your CoachIntel Account</h2>
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
          {/* Server Action Signup Form */}
          <SignupForm />
          
          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">Or continue with</span>
            </div>
          </div>
          
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
    <Suspense fallback={<LoadingOverlay message="Loading signup page..." />}>
      <SignupPageContent />
    </Suspense>
  );
}
