'use client';

import { signIn } from "next-auth/react";

export default function GoogleLoginButton() {
  const handleGoogleLogin = () => {
    signIn('google', { 
      callbackUrl: '/dashboard',
      redirect: true 
    });
  };

  return (
    <button
      type="button"
      className="flex items-center justify-center gap-2 border border-gray-300 bg-white text-gray-700 font-medium rounded py-2 w-full hover:bg-gray-100 transition"
      onClick={handleGoogleLogin}
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 48 48"
        className="inline-block align-middle"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g>
          <path fill="#4285F4" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.23l6.85-6.85C35.64 2.13 30.18 0 24 0 14.82 0 6.73 5.48 2.69 13.44l7.98 6.2C12.13 13.13 17.62 9.5 24 9.5z" />
          <path fill="#34A853" d="M46.1 24.55c0-1.64-.15-3.22-.42-4.74H24v9.01h12.42c-.54 2.9-2.18 5.36-4.65 7.01l7.2 5.6C43.98 37.13 46.1 31.36 46.1 24.55z" />
          <path fill="#FBBC05" d="M10.67 28.65c-1.13-3.36-1.13-6.94 0-10.3l-7.98-6.2C.9 16.18 0 19.98 0 24c0 4.02.9 7.82 2.69 11.55l7.98-6.2z" />
          <path fill="#EA4335" d="M24 48c6.18 0 11.64-2.05 15.53-5.59l-7.2-5.6c-2.01 1.35-4.6 2.14-8.33 2.14-6.38 0-11.87-3.63-14.33-8.89l-7.98 6.2C6.73 42.52 14.82 48 24 48z" />
          <path fill="none" d="M0 0h48v48H0z" />
        </g>
      </svg>
      Continue with Google
    </button>
  );
}
