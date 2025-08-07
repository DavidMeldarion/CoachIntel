'use client';

import Link from "next/link";
import { Suspense, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useSearchParams, useRouter } from "next/navigation";
import GoogleLoginButton from "../../components/GoogleLoginButton";
import { AuthErrorBoundary } from "../../components/ErrorBoundary";
import { LoadingOverlay } from "../../components/LoadingStates";

function LoginPageContent() {
  const { data: session, status } = useSession();
  const searchParams = useSearchParams();
  const router = useRouter();
  const error = searchParams.get('error');

  useEffect(() => {
    // If authenticated, redirect immediately
    if (status === 'authenticated' && session) {
      console.log('[LoginPage] User authenticated, redirecting to dashboard');
      router.replace('/dashboard');
    }
  }, [status, session, router]);

  // Show loading while checking authentication
  if (status === 'loading') {
    return <LoadingOverlay message="Checking authentication..." />;
  }

  // If authenticated, show loading while redirecting
  if (status === 'authenticated') {
    return <LoadingOverlay message="Redirecting to dashboard..." />;
  }

  return (
    <AuthErrorBoundary>
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <h2 className="text-2xl font-bold mb-6 text-blue-700">Login to CoachIntel</h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 max-w-md">
            <p className="text-sm">
              <strong>Authentication Error:</strong> {error}
            </p>
            <p className="text-xs mt-1">Please try logging in again.</p>
          </div>
        )}
        
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
          {/* Google OAuth Login with NextAuth */}
          <GoogleLoginButton />
          
          <Link
            href="/signup"
            className="text-blue-600 hover:underline mt-2 text-center"
          >
            Don&apos;t have an account? Sign up
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
