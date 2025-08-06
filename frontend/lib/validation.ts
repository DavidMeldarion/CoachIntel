import { z } from 'zod';

// Enhanced password validation schema
const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters long")
  .regex(/[A-Za-z]/, "Password must contain at least one letter")
  .regex(/\d/, "Password must contain at least one number")
  .regex(/[^A-Za-z0-9]/, "Password must contain at least one special character")
  .max(128, "Password must be less than 128 characters");

// Enhanced email validation schema
const emailSchema = z
  .string()
  .email("Please enter a valid email address")
  .min(1, "Email is required")
  .max(254, "Email must be less than 254 characters")
  .transform(email => email.toLowerCase().trim());

// Name validation schema
const nameSchema = z
  .string()
  .trim()
  .min(1, "Name is required")
  .max(50, "Name must be less than 50 characters")
  .regex(/^[a-zA-Z\s\-'\.]+$/, "Name can only contain letters, spaces, hyphens, apostrophes, and periods");

// Phone number validation schema
const phoneSchema = z
  .string()
  .optional()
  .refine((phone) => {
    if (!phone || phone.trim() === '') return true;
    const phoneRegex = /^[\+]?[\d\s\-\(\)]{10,20}$/;
    return phoneRegex.test(phone);
  }, {
    message: "Please enter a valid phone number"
  });

// Address validation schema
const addressSchema = z
  .string()
  .optional()
  .refine((address) => {
    if (!address || address.trim() === '') return true;
    return address.length <= 200;
  }, {
    message: "Address must be less than 200 characters"
  });

// API key validation schema
const apiKeySchema = z
  .string()
  .optional()
  .refine((key) => {
    if (!key || key.trim() === '') return true;
    return key.length >= 10 && key.length <= 100;
  }, {
    message: "API key must be between 10 and 100 characters"
  });

// Login form validation schema
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Password is required")
});

// Signup form validation schema
export const signupSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  firstName: nameSchema,
  lastName: nameSchema
});

// Profile form validation schema
export const profileSchema = z.object({
  email: emailSchema,
  firstName: nameSchema,
  lastName: nameSchema,
  phone: phoneSchema,
  address: addressSchema,
  firefliesApiKey: apiKeySchema,
  zoomJwt: apiKeySchema
});

// Password change validation schema
export const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, "Current password is required"),
  newPassword: passwordSchema,
  confirmPassword: z.string().min(1, "Please confirm your new password")
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

// Meeting form validation schema
export const meetingSchema = z.object({
  title: z.string().min(1, "Meeting title is required").max(200, "Title must be less than 200 characters"),
  description: z.string().optional(),
  date: z.string().min(1, "Meeting date is required"),
  duration: z.number().min(1, "Duration must be at least 1 minute").max(1440, "Duration cannot exceed 24 hours"),
  participants: z.array(z.string().email("Invalid participant email")).min(1, "At least one participant is required")
});

// File upload validation schema
export const fileUploadSchema = z.object({
  file: z.instanceof(File, { message: "Please select a file" })
    .refine((file) => file.size <= 50 * 1024 * 1024, "File size must be less than 50MB")
    .refine(
      (file) => ['audio/mpeg', 'audio/wav', 'audio/mp4', 'video/mp4', 'video/mpeg'].includes(file.type),
      "File must be an audio or video file"
    ),
  title: z.string().min(1, "Title is required").max(200, "Title must be less than 200 characters"),
  description: z.string().optional()
});

// Search form validation schema
export const searchSchema = z.object({
  query: z.string().min(1, "Search query is required").max(100, "Search query must be less than 100 characters"),
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
  type: z.enum(['all', 'meetings', 'transcripts', 'summaries']).default('all')
}).refine((data) => {
  if (data.dateFrom && data.dateTo) {
    return new Date(data.dateFrom) <= new Date(data.dateTo);
  }
  return true;
}, {
  message: "End date must be after start date",
  path: ["dateTo"]
});

// API key management schema
export const apiKeyManagementSchema = z.object({
  service: z.enum(['fireflies', 'zoom']),
  apiKey: z.string().min(10, "API key must be at least 10 characters").max(100, "API key must be less than 100 characters"),
  description: z.string().optional()
});

// Notification preferences schema
export const notificationPreferencesSchema = z.object({
  emailNotifications: z.boolean().default(true),
  transcriptReady: z.boolean().default(true),
  summaryReady: z.boolean().default(true),
  weeklyDigest: z.boolean().default(false),
  marketingEmails: z.boolean().default(false)
});

// Export type definitions for TypeScript
export type LoginFormData = z.infer<typeof loginSchema>;
export type SignupFormData = z.infer<typeof signupSchema>;
export type ProfileFormData = z.infer<typeof profileSchema>;
export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;
export type MeetingFormData = z.infer<typeof meetingSchema>;
export type FileUploadFormData = z.infer<typeof fileUploadSchema>;
export type SearchFormData = z.infer<typeof searchSchema>;
export type ApiKeyManagementFormData = z.infer<typeof apiKeyManagementSchema>;
export type NotificationPreferencesFormData = z.infer<typeof notificationPreferencesSchema>;

// Validation helper functions
export function validateEmail(email: string): boolean {
  try {
    emailSchema.parse(email);
    return true;
  } catch {
    return false;
  }
}

export function validatePassword(password: string): { isValid: boolean; errors: string[] } {
  try {
    passwordSchema.parse(password);
    return { isValid: true, errors: [] };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        isValid: false,
        errors: error.issues.map(err => err.message)
      };
    }
    return { isValid: false, errors: ['Invalid password'] };
  }
}

// Form validation helper
export function getFormErrors(error: z.ZodError): Record<string, string> {
  const errors: Record<string, string> = {};
  error.issues.forEach((err) => {
    if (err.path.length > 0) {
      errors[err.path[0] as string] = err.message;
    }
  });
  return errors;
}
