import { getServerApiBase } from './serverApi';

// Thin helper for server-side backend calls (route handlers, RSC loaders, server actions)
export async function backendFetch(path: string, init?: RequestInit) {
  const API_BASE = getServerApiBase();
  const href = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  return fetch(href, { cache: 'no-store', ...init });
}
