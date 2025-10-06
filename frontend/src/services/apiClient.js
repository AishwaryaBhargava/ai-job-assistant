const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://ai-job-assistant-backend.onrender.com";

export default API_BASE;

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");
  const init = { ...options };
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  init.headers = headers;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (networkErr) {
    const error = new Error("Unable to connect to API server.");
    error.status = 0;
    throw error;
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || data.message || JSON.stringify(data);
    } catch {
      // ignore JSON parse failures
    }
    const error = new Error(detail || "Request failed");
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export function getApiBase() {
  return API_BASE;
}
