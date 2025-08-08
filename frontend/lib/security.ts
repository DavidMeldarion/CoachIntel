// Security Configuration for CoachIntel
// This file documents our authentication and security implementation

export const SECURITY_CONFIG = {
  // Authentication settings
  auth: {
    // Session management
    session: {
      strategy: 'jwt',
      maxAge: 30 * 24 * 60 * 60, // 30 days
      updateAge: 24 * 60 * 60, // 24 hours
    },
    
    // JWT settings
    jwt: {
      secret: process.env.NEXTAUTH_SECRET,
      encryption: true,
    },
    
    // OAuth providers
    providers: {
      google: {
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        scopes: ['openid', 'email', 'profile'],
      },
    },
  },

  // Route protection
  routes: {
    public: ['/', '/login', '/signup'],
    protected: ['/dashboard', '/profile', '/timeline', '/upload', '/apikeys'],
    api: ['/api/auth'],
  },

  // Security headers
  headers: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' *.vercel.com *.google.com *.gstatic.com",
      "style-src 'self' 'unsafe-inline' *.googleapis.com",
      "img-src 'self' data: *.googleusercontent.com *.google.com",
      "connect-src 'self' *.vercel.com *.google.com wss:",
      "font-src 'self' *.googleapis.com *.gstatic.com",
      "frame-src 'self' *.google.com",
    ].join('; '),
  },

  // CORS settings
  cors: {
    origin: process.env.NODE_ENV === 'production' 
      ? ['https://www.coachintel.ai', 'https://coachintel.ai']
      : ['http://localhost:3000', 'http://127.0.0.1:3000'],
    credentials: true,
  },

  // Rate limiting (to be implemented)
  rateLimit: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
  },
} as const;

// Security checklist for production
export const SECURITY_CHECKLIST = [
  '✅ NextAuth.js with JWT tokens',
  '✅ Google OAuth 2.0 integration',
  '✅ Route-based authentication middleware',
  '✅ Security headers (XSS, CSRF, etc.)',
  '✅ Content Security Policy',
  '✅ HTTPS enforcement in production',
  '✅ Secure cookie settings',
  '✅ Backend token validation',
  '⏳ Rate limiting (to be implemented)',
  '⏳ Session invalidation on logout',
  '⏳ Audit logging',
] as const;

// Environment variables required for security
export const REQUIRED_ENV_VARS = [
  'NEXTAUTH_SECRET',
  'NEXTAUTH_URL',
  'GOOGLE_CLIENT_ID',
  'GOOGLE_CLIENT_SECRET',
] as const;
