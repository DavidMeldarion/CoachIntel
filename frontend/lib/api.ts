import axios from "axios";
import { getApiUrl } from "./apiUrl";

// Configure axios to include credentials by default
axios.defaults.withCredentials = true;

export async function fetchSessions() {
  const res = await axios.get(getApiUrl("/sessions/"));
  return res.data;
}

export async function uploadAudio(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post(getApiUrl("/upload-audio/"), formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}