'use client';

import Link from "next/link";
import { Suspense, useEffect, useMemo } from "react";
import { useSession } from "next-auth/react";
import { useSearchParams, useRouter } from "next/navigation";
import GoogleLoginButton from "../../components/GoogleLoginButton";
import { AuthErrorBoundary } from "../../components/ErrorBoundary";
import { LoadingOverlay } from "../../components/LoadingStates";

function isSafeCallbackUrl(url: string | null) {
  if (!url) return false;
  // Only allow same-origin relative paths
  if (!url.startsWith('/')) return false;
  // Disallow auth-related endpoints that can loop
  if (url.startsWith('/login') || url.startsWith('/signup') || url.startsWith('/api/auth')) return false;
  return true;
}

function LoginPageContent() {
  const { data: session, status } = useSession();
  const searchParams = useSearchParams();
  const router = useRouter();
  const error = searchParams.get('error');
  const rawCallback = searchParams.get('callbackUrl');
  const callbackUrl = useMemo(() => (isSafeCallbackUrl(rawCallback) ? rawCallback! : '/dashboard'), [rawCallback]);

  // Redirect authenticated users to a safe target (default: /dashboard)
  useEffect(() => {
    if (status === 'authenticated' && session) {
      router.replace(callbackUrl);
    }
  }, [status, session, router, callbackUrl]);

  // Show loading while checking authentication
  if (status === 'loading') {
    return <LoadingOverlay message="Checking authentication..." />;
  }

  // If authenticated, show redirect overlay to avoid blank screen
  if (status === 'authenticated' && session) {
    return <LoadingOverlay message="Redirecting..." />;
  }

  return (
    <AuthErrorBoundary>
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <h2 className="text-2xl font-bold mb-6 text-blue-700">Login to CoachIntel</h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 max-w-md">
            <p className="text-sm">
              <strong>Authentication Error:</strong> {
                error === 'CredentialsSignin' ? 'Invalid credentials. Please try again.' :
                error === 'OAuthSignin' ? 'Error connecting to Google. Please try again.' :
                error === 'OAuthCallback' ? 'Error during authentication. Please try again.' :
                error
              }
            </p>
          </div>
        )}
        
        <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100">
          {/* Google OAuth Login with NextAuth */}
          <GoogleLoginButton callbackUrl={callbackUrl} />
          
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
