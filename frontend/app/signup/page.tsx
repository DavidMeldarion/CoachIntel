"use client";
import { useState } from "react";
import { upsertUserProfile } from "../../lib/userApi";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email) {
      setError("Email is required.");
      return;
    }
    setLoading(true);
    try {
      // Check if user already exists
      const res = await fetch(`${process.env.NEXT_PUBLIC_BROWSER_API_URL || 'http://localhost:8000'}/user/${encodeURIComponent(email)}`);
      if (res.ok) {
        setError("Account already exists. Please log in.");
        setTimeout(() => router.push("/login"), 1500);
        setLoading(false);
        return;
      }
    } catch {}
    try {
      // Optionally, create a user record with just the email here if needed
      localStorage.setItem("userEmail", email);
      router.push("/profile/complete-profile");
    } catch {
      setError("Signup failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p className="text-gray-600">Signing up...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50">
      <h2 className="text-2xl font-bold mb-6 text-blue-700">Sign Up</h2>
      <form className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md flex flex-col gap-6 border border-gray-100" onSubmit={handleSubmit}>
        <label className="font-semibold text-gray-700">Email</label>
        <input
          type="email"
          className="border border-gray-300 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="Enter your email"
          required
        />
        {error && <div className="text-red-500 text-sm text-center">{error}</div>}
        <button type="submit" className="w-full bg-blue-600 text-white font-semibold rounded py-2 hover:bg-blue-700 transition">Continue</button>
        <button
          type="button"
          className="flex items-center justify-center gap-2 border border-gray-300 bg-white text-gray-700 font-medium rounded py-2 w-full hover:bg-gray-100 transition"
          onClick={() => window.location.href = (process.env.NEXT_PUBLIC_BROWSER_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/auth/google?intent=signup"}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 48 48"
            className="inline-block align-middle"
            xmlns="http://www.w3.org/2000/svg"
          >
            <g>
              <path fill="#4285F4" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.23l6.85-6.85C35.64 2.13 30.18 0 24 0 14.82 0 6.73 5.48 2.69 13.44l7.98 6.2C12.13 13.13 17.62 9.5 24 9.5z"/>
              <path fill="#34A853" d="M46.1 24.55c0-1.64-.15-3.22-.42-4.74H24v9.01h12.42c-.54 2.9-2.18 5.36-4.65 7.01l7.2 5.6C43.98 37.13 46.1 31.36 46.1 24.55z"/>
              <path fill="#FBBC05" d="M10.67 28.65c-1.13-3.36-1.13-6.94 0-10.3l-7.98-6.2C.9 16.18 0 19.98 0 24c0 4.02.9 7.82 2.69 11.55l7.98-6.2z"/>
              <path fill="#EA4335" d="M24 48c6.18 0 11.64-2.05 15.53-5.59l-7.2-5.6c-2.01 1.35-4.6 2.14-8.33 2.14-6.38 0-11.87-3.63-14.33-8.89l-7.98 6.2C6.73 42.52 14.82 48 24 48z"/>
              <path fill="none" d="M0 0h48v48H0z"/>
            </g>
          </svg>
          Continue with Google
        </button>
        <Link href="/login" className="text-blue-600 hover:underline mt-2 text-center">Already have an account? Log in</Link>
      </form>
    </main>
  );
}
