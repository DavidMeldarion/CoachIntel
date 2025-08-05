import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_BROWSER_API_URL || "http://localhost:8000";

// Configure axios to include credentials by default
axios.defaults.withCredentials = true;

export async function getUserProfile(email: string) {
  const res = await axios.get(`${API_BASE}/user/${encodeURIComponent(email)}`);
  return res.data;
}

export async function upsertUserProfile(profile: {
  email: string;
  name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
}) {
  const res = await axios.post(`${API_BASE}/user`, profile);
  return res.data;
}
