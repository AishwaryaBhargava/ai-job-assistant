import { apiFetch } from "./apiClient";

export async function fetchRealtimeJobs(params = {}) {
  const query = new URLSearchParams();

  if (params.what) query.set("what", params.what);
  if (params.where) query.set("where", params.where);
  if (params.maxDaysOld) query.set("max_days_old", params.maxDaysOld);
  if (params.salaryMin) query.set("salary_min", params.salaryMin);
  if (params.salaryMax) query.set("salary_max", params.salaryMax);
  if (params.fullTime) query.set("full_time", "true");
  if (params.contract) query.set("contract", "true");
  if (params.remoteOnly) query.set("remote_only", "true");

  const page = params.page ?? 1;
  const pageSize = params.page_size ?? params.pageSize ?? 20;
  query.set("page", String(page));
  query.set("page_size", String(pageSize));

  const qs = query.toString();
  const path = qs ? `/jobs/realtime?${qs}` : "/jobs/realtime";
  return apiFetch(path);
}

export async function saveJob(jobData, token) {
  return apiFetch("/applications/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(jobData),
  });
}

export async function unsaveJob(jobId, token) {
  return apiFetch(`/applications/unsave/${jobId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchSavedJobs(userId, token) {
  return apiFetch(`/applications/${userId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchResumeScore(jobDescription, token) {
  return apiFetch(`/resume/score`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ job_description: jobDescription }),
  });
}
