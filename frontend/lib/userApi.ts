import axios from "axios";
import { getApiUrl } from "./apiUrl";

// Configure axios to include credentials by default
axios.defaults.withCredentials = true;

export async function getUserProfile(email: string) {
  const res = await axios.get(getApiUrl(`/user/${encodeURIComponent(email)}`));
  return res.data;
}

export async function upsertUserProfile(profile: {
  email: string;
  name?: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
}) {
  const res = await axios.post(getApiUrl("/user"), profile);
  return res.data;
}
