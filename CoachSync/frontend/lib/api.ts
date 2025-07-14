import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_BROWSER_API_URL || "http://localhost:8000";

// Configure axios to include credentials by default
axios.defaults.withCredentials = true;

export async function fetchSessions() {
  const res = await axios.get(`${API_BASE}/sessions/`);
  return res.data;
}

export async function uploadAudio(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post(`${API_BASE}/upload-audio/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}