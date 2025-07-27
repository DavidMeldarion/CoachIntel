"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useUser, User } from "../../lib/userContext";

// Use the same type as context for full type safety
export type UserProfile = {
  email: string;
  name: string;
  first_name: string;
  last_name: string;
  fireflies_api_key?: string;
  zoom_jwt?: string;
  phone?: string;
  address?: string;
};

export default function Profile() {
  const router = useRouter();
  const { user, loading: userLoading, refreshUser } = useUser();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<UserProfile>({
    email: "",
    name: "",
    first_name: "",
    last_name: "",
    fireflies_api_key: "",
    zoom_jwt: "",
    phone: "",
    address: "",
  });
  const [firefliesTestStatus, setFirefliesTestStatus] = useState<string>("");
  const [testingFireflies, setTestingFireflies] = useState(false);

  useEffect(() => {
    if (user) {
      // Map context user to local UserProfile type, ensuring required fields
      setProfile({
        email: user.email,
        name: user.name || "",
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        fireflies_api_key: user.fireflies_api_key || "",
        zoom_jwt: user.zoom_jwt || "",
        phone: user.phone || "",
        address: user.address || "",
      });
      setFormData({
        email: user.email,
        name: user.name || "",
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        fireflies_api_key: user.fireflies_api_key || "",
        zoom_jwt: user.zoom_jwt || "",
        phone: user.phone || "",
        address: user.address || "",
      });
      setLoading(false);
    } else {
      router.push("/login");
    }
  }, [user, router]);

  async function handleSave() {
    setError("");
    setSuccess("");
    try {
      const res = await fetch(
        process.env.NEXT_PUBLIC_BROWSER_API_URL + "/user",
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify(formData),
        }
      );

      if (res.ok) {
        const updatedProfile = await res.json();
        setProfile(updatedProfile);
        setIsEditing(false);
        setSuccess("Profile updated successfully!");
        await refreshUser(); // Refresh context after profile update
      } else {
        setError("Failed to update profile");
      }
    } catch (err) {
      setError("Failed to update profile");
    }
  }
  function handleCancel() {
    setFormData(
      profile || {
        email: "",
        name: "",
        first_name: "",
        last_name: "",
        fireflies_api_key: "",
        zoom_jwt: "",
        phone: "",
        address: "",
      }
    );
    setIsEditing(false);
    setError("");
    setSuccess("");
  }

  async function handleTestFireflies() {
    setFirefliesTestStatus("");
    setTestingFireflies(true);
    try {
      // Call proxy endpoint, which uses session context
      const res = await fetch(`/api/test-fireflies`);
      if (res.ok) {
        setFirefliesTestStatus("Connection successful!");
      } else {
        const errorText = await res.text();
        setFirefliesTestStatus("Connection failed. " + errorText);
      }
    } catch {
      setFirefliesTestStatus("Connection failed. Please check your key.");
    } finally {
      setTestingFireflies(false);
    }
  }

  if (loading) {
    return (
      <main className="flex items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </main>
    );
  }
  if (error) {
    return (
      <main className="flex items-center justify-center min-h-screen p-8 bg-gray-50">
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded mb-4">
          {error}
        </div>
      </main>
    );
  }
  // Only show profile UI when not loading and no error
  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-100">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-blue-700">My Profile</h1>
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-semibold transition"
              >
                Edit Profile
              </button>
            )}
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
              {success}
            </div>
          )}

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                disabled
                className="w-full border border-gray-300 rounded px-4 py-2 bg-gray-100 text-gray-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Email cannot be changed
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                First Name
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) =>
                  setFormData({ ...formData, first_name: e.target.value })
                }
                disabled={!isEditing}
                className={`w-full border border-gray-300 rounded px-4 py-2 ${
                  isEditing
                    ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                    : "bg-gray-50"
                }`}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Last Name
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) =>
                  setFormData({ ...formData, last_name: e.target.value })
                }
                disabled={!isEditing}
                className={`w-full border border-gray-300 rounded px-4 py-2 ${
                  isEditing
                    ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                    : "bg-gray-50"
                }`}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              <input
                type="tel"
                value={formData.phone || ""}
                onChange={(e) =>
                  setFormData({ ...formData, phone: e.target.value })
                }
                disabled={!isEditing}
                className={`w-full border border-gray-300 rounded px-4 py-2 ${
                  isEditing
                    ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                    : "bg-gray-50"
                }`}
                placeholder="Optional"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Address
              </label>
              <textarea
                value={formData.address || ""}
                onChange={(e) =>
                  setFormData({ ...formData, address: e.target.value })
                }
                disabled={!isEditing}
                rows={3}
                className={`w-full border border-gray-300 rounded px-4 py-2 ${
                  isEditing
                    ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                    : "bg-gray-50"
                }`}
                placeholder="Optional"
              />
            </div>

            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold text-gray-700 mb-4">
                API Integration
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fireflies.ai API Key
                  </label>
                  <div className="flex gap-2 items-center">
                    <input
                      type="password"
                      value={formData.fireflies_api_key || ""}
                      onChange={(e) =>
                        setFormData({ ...formData, fireflies_api_key: e.target.value })
                      }
                      disabled={!isEditing}
                      className={`w-full border border-gray-300 rounded px-4 py-2 ${
                        isEditing
                          ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                          : "bg-gray-50"
                      }`}
                      placeholder="Optional - for meeting transcription"
                    />
                    {!isEditing && profile?.fireflies_api_key && (
                      <button
                        type="button"
                        className={`px-3 py-2 rounded bg-blue-600 text-white font-semibold transition hover:bg-blue-700 ${
                          testingFireflies ? "opacity-50 cursor-not-allowed" : ""
                        }`}
                        onClick={handleTestFireflies}
                        disabled={testingFireflies}
                      >
                        {testingFireflies ? (
                          <span className="flex items-center gap-2">
                            <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                            Testing...
                          </span>
                        ) : (
                          "Test Connection"
                        )}
                      </button>
                    )}
                  </div>
                  {firefliesTestStatus && (
                    <div
                      className={`mt-2 text-sm text-center ${
                        firefliesTestStatus.includes("successful")
                          ? "text-green-700"
                          : "text-red-600"
                      }`}
                    >
                      {firefliesTestStatus}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Zoom JWT Token
                  </label>
                  <input
                    type="password"
                    value={formData.zoom_jwt || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, zoom_jwt: e.target.value })
                    }
                    disabled={!isEditing}
                    className={`w-full border border-gray-300 rounded px-4 py-2 ${
                      isEditing
                        ? "focus:outline-none focus:ring-2 focus:ring-blue-200"
                        : "bg-gray-50"
                    }`}
                    placeholder="Optional - for Zoom integration"
                  />
                </div>
              </div>
            </div>

            {isEditing && (
              <div className="flex gap-4 pt-6 border-t">
                <button
                  onClick={handleSave}
                  className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-semibold transition"
                >
                  Save Changes
                </button>
                <button
                  onClick={handleCancel}
                  className="px-6 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 font-semibold transition"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
