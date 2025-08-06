'use server';

import { redirect } from 'next/navigation';
import { createSession, deleteSession } from './session';
import { getApiUrl } from './apiUrl';
import { loginSchema, signupSchema, getFormErrors } from './validation';

export interface FormState {
  errors?: {
    email?: string[];
    password?: string[];
    firstName?: string[];
    lastName?: string[];
    general?: string[];
  };
  message?: string;
  success?: boolean;
}

export async function signup(state: FormState | undefined, formData: FormData): Promise<FormState> {
  try {
    // Validate form fields using enhanced schema
    const validationResult = signupSchema.safeParse({
      email: formData.get('email'),
      password: formData.get('password'),
      firstName: formData.get('firstName'),
      lastName: formData.get('lastName')
    });

    if (!validationResult.success) {
      return {
        errors: getFormErrors(validationResult.error) as FormState['errors']
      };
    }

    const { email, password, firstName, lastName } = validationResult.data;

    // Call backend to create user
    const response = await fetch(getApiUrl('/signup'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        email, 
        password, 
        first_name: firstName, 
        last_name: lastName 
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        errors: {
          general: [errorData.error || 'Failed to create account']
        }
      };
    }

    const userData = await response.json();

    // Create session - extract user info from response
    const userId = userData.user?.id || userData.user?.email || email;
    const userEmail = userData.user?.email || email;
    await createSession(userId, userEmail);

    return {
      success: true,
      message: 'Account created successfully!'
    };

  } catch (error) {
    console.error('Signup error:', error);
    return {
      errors: {
        general: ['An unexpected error occurred. Please try again.']
      }
    };
  }
}

export async function login(state: FormState | undefined, formData: FormData): Promise<FormState> {
  try {
    // Validate form fields using enhanced schema
    const validationResult = loginSchema.safeParse({
      email: formData.get('email'),
      password: formData.get('password')
    });

    if (!validationResult.success) {
      return {
        errors: getFormErrors(validationResult.error) as FormState['errors']
      };
    }

    const { email, password } = validationResult.data;

    // Call backend to authenticate user
    const response = await fetch(getApiUrl('/login'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        errors: {
          general: [errorData.error || 'Invalid email or password']
        }
      };
    }

    const userData = await response.json();

    // Create session - extract user info from response
    const userId = userData.user?.id || userData.user?.email || email;
    const userEmail = userData.user?.email || email;
    await createSession(userId, userEmail);

  } catch (error) {
    console.error('Login error:', error);
    return {
      errors: {
        general: ['An unexpected error occurred. Please try again.']
      }
    };
  }

  // Redirect to dashboard after successful login
  redirect('/dashboard');
}

export async function logout(): Promise<void> {
  try {
    // Call backend logout endpoint
    await fetch(getApiUrl('/logout'), {
      method: 'POST',
      credentials: 'include',
    });
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always delete local session
    deleteSession();
    redirect('/');
  }
}
