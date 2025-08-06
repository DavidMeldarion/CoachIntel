import Link from "next/link";
import { Suspense } from "react";
import LoginForm from "../../components/LoginForm";
import GoogleLoginButton from "../../components/GoogleLoginButton";
import { AuthErrorBoundary } from "../../components/ErrorBoundary";
import { LoadingOverlay } from "../../components/LoadingStates";

function LoginPageContent() {
  return (
    <AuthErrorBoundary>
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <h2 className="text-2xl font-bold mb-6 text-blue-700">Login to CoachIntel</h2>
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
          {/* Server Action Login Form */}
          <LoginForm />
          
          {/* Google OAuth Login */}
          <GoogleLoginButton />
          
          <Link
            href="/signup"
            className="text-blue-600 hover:underline mt-2 text-center"
          >
            Don't have an account? Sign up
          </Link>
        </div>
      </main>
    </AuthErrorBoundary>
  );
}

export default function Login() {
  return (
    <Suspense fallback={<LoadingOverlay message="Loading login page..." />}>
      <LoginPageContent />
    </Suspense>
  );
}
