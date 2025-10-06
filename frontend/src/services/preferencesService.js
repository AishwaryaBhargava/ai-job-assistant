import { apiFetch } from "./apiClient";

export async function fetchPreferences() {
  return apiFetch("/preferences/");
}

export async function persistPreferences(payload) {
  return apiFetch("/preferences/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

