'use server';

import { redirect } from 'next/navigation';
import { createSession, deleteSession } from './session';
import { getApiUrl } from './apiUrl';
import { z } from 'zod';

// Form validation schemas
export const SignupFormSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email.' }).trim(),
  password: z
    .string()
    .min(8, { message: 'Be at least 8 characters long' })
    .regex(/[a-zA-Z]/, { message: 'Contain at least one letter.' })
    .regex(/[0-9]/, { message: 'Contain at least one number.' })
    .regex(/[^a-zA-Z0-9]/, {
      message: 'Contain at least one special character.',
    })
    .trim(),
});

export const LoginFormSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email.' }).trim(),
  password: z.string().min(1, { message: 'Password is required.' }).trim(),
});

export type FormState =
  | {
      errors?: {
        email?: string[];
        password?: string[];
      };
      message?: string;
    }
  | undefined;

export async function signup(state: FormState, formData: FormData): Promise<FormState> {
  // 1. Validate form fields
  const validatedFields = SignupFormSchema.safeParse({
    email: formData.get('email'),
    password: formData.get('password'),
  });

  // If form validation fails, return errors early
  if (!validatedFields.success) {
    return {
      errors: validatedFields.error.flatten().fieldErrors,
    };
  }

  const { email, password } = validatedFields.data;

  try {
    // 2. Call backend to create user
    const response = await fetch(getApiUrl('/signup'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        message: errorData.detail || 'Failed to create account',
      };
    }

    const userData = await response.json();

    // 3. Create session
    await createSession(userData.user.id || userData.user.email, userData.user.email);

    // 4. Redirect user
    redirect('/dashboard');
  } catch (error) {
    return {
      message: 'An error occurred while creating your account.',
    };
  }
}

export async function login(state: FormState, formData: FormData): Promise<FormState> {
  // 1. Validate form fields
  const validatedFields = LoginFormSchema.safeParse({
    email: formData.get('email'),
    password: formData.get('password'),
  });

  // If form validation fails, return errors early
  if (!validatedFields.success) {
    return {
      errors: validatedFields.error.flatten().fieldErrors,
    };
  }

  const { email, password } = validatedFields.data;

  try {
    // 2. Call backend to authenticate user
    const response = await fetch(getApiUrl('/login'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      return {
        message: 'Invalid email or password.',
      };
    }

    const userData = await response.json();

    // 3. Create session
    await createSession(userData.user.id || userData.user.email, userData.user.email);

    // 4. Redirect user
    redirect('/dashboard');
  } catch (error) {
    return {
      message: 'An error occurred during login.',
    };
  }
}

export async function logout() {
  // 1. Delete the session cookie
  await deleteSession();
  
  // 2. Call backend logout to clear any server-side sessions
  try {
    await fetch(getApiUrl('/logout'), {
      method: 'POST',
    });
  } catch (error) {
    // Ignore backend logout errors
    console.error('Backend logout failed:', error);
  }

  // 3. Redirect to login page
  redirect('/login');
}
