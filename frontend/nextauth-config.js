// nextauth-config.js - Force correct NEXTAUTH_URL before any NextAuth imports
if (typeof window === 'undefined' && process.env.NODE_ENV === 'production') {
  // Server-side only
  const correctUrl = 'https://www.coachintel.ai/frontend';
  process.env.NEXTAUTH_URL = correctUrl;
  process.env.NEXTAUTH_URL_INTERNAL = correctUrl;
  
  console.log('[NextAuth Config] Forcing NEXTAUTH_URL to:', correctUrl);
}

module.exports = {};
