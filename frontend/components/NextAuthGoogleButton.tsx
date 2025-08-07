'use client';

import { signIn } from "next-auth/react";

export default function NextAuthGoogleButton() {
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
          <path fill="#34A853" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.2C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.79l7.97-6.2z" />
          <path fill="#EA4335" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.2C6.51 42.62 14.62 48 24 48z" />
          <path fill="none" d="M0 0h48v48H0z" />
        </g>
      </svg>
      Continue with Google
    </button>
  );
}
