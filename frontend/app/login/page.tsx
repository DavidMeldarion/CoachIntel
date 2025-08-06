import Link from "next/link";
import { Suspense } from "react";
import LoginForm from "../../components/LoginForm";
import GoogleLoginButton from "../../components/GoogleLoginButton";

function LoginPageContent() {
  return (
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
  );
}

export default function Login() {
  return (
    <Suspense fallback={
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </main>
    }>
      <LoginPageContent />
    </Suspense>
  );
}
