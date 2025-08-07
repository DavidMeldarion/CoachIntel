import axios from "axios";
import { getSession } from "next-auth/react";
import { getApiUrl } from "./apiUrl";

// Configure axios to include credentials by default
axios.defaults.withCredentials = true;

// Helper function to get headers with NextAuth user email
async function getAuthHeaders() {
  const session = await getSession();
  return session?.user?.email 
    ? { "x-user-email": session.user.email }
    : {};
}

export async function fetchSessions() {
  const headers = await getAuthHeaders();
  const res = await axios.get(getApiUrl("/sessions/"), { headers });
  return res.data;
}

export async function uploadAudio(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const headers = await getAuthHeaders();
  const res = await axios.post(getApiUrl("/upload-audio/"), formData, {
    headers: { 
      "Content-Type": "multipart/form-data",
      ...headers 
    },
  });
  return res.data;
}