'use client';

import { useFormState } from 'react-dom';
import { useFormStatus } from 'react-dom';
import { signup } from '../lib/auth-actions';

function SubmitButton() {
  const { pending } = useFormStatus();
  
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full bg-blue-600 text-white font-semibold rounded py-2 hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {pending ? 'Creating account...' : 'Create Account'}
    </button>
  );
}

export default function SignupForm() {
  const [state, action] = useFormState(signup, undefined);

  return (
    <form action={action} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          placeholder="Email"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
        />
        {state?.errors?.email && (
          <p className="mt-1 text-sm text-red-600">{state.errors.email}</p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          placeholder="Password"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
        />
        {state?.errors?.password && (
          <div className="mt-1">
            <p className="text-sm text-gray-600">Password must:</p>
            <ul className="mt-1 text-sm text-red-600">
              {state.errors.password.map((error) => (
                <li key={error}>- {error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {state?.message && (
        <p className="text-sm text-red-600">{state.message}</p>
      )}

      <SubmitButton />
    </form>
  );
}
