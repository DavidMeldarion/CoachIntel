// Centralized theme tokens for CoachIntel frontend
export const COLORS = {
  primary: 'rgb(35 150 243)',
  primary600: 'rgb(35 150 243)',
  primary700: 'rgb(29 78 216)',
  onPrimary: 'rgb(255 255 255)',
  accent: 'rgb(15 23 42)',
  muted: 'rgb(100 116 139)',
  border: 'rgb(226 232 240)'
};

export const RADIUS = {
  sm: '0.25rem',
  md: '0.5rem',
  lg: '0.75rem'
};

export const FONT = {
  sans: "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
};

export const CONSENT_VERSION = process.env.NEXT_PUBLIC_CONSENT_VERSION || 'v1';
