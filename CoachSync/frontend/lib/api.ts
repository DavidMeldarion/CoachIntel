import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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