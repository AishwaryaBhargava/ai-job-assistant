// src/pages/JobListings.jsx
import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import {
  fetchRealtimeJobs,
  saveJob,
  unsaveJob,
  fetchSavedJobs,
  fetchResumeScore,
} from "../services/jobsService";
import "./PageLayout.css";
import "./JobListings.css";

const PAGE_SIZE = 20;

export default function JobListings() {
  const defaultFilters = {
    what: "",
    where: "",
    salaryMin: "",
    salaryMax: "",
    maxDaysOld: "",
    remoteOnly: false,
    fullTime: false,
    contract: false,
    workType: "",
    employmentType: "",
  };

  const [filters, setFilters] = useState(defaultFilters);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [expanded, setExpanded] = useState([]);
  const [savedJobs, setSavedJobs] = useState([]);
  const [resumeScores, setResumeScores] = useState({});

  const token = localStorage.getItem("token");
  const userId = localStorage.getItem("user_id");

  // ----------------------------
  // 🔹 Initial load
  // ----------------------------
  useEffect(() => {
    loadJobs(1, filters);
    if (token && userId) loadSavedJobs(userId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----------------------------
  // 🔹 Load jobs (Adzuna API)
  // ----------------------------
  async function loadJobs(nextPage = page, activeFilters = filters) {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRealtimeJobs({
        ...activeFilters,
        page: nextPage,
        pageSize: PAGE_SIZE,
      });
      setJobs(data.items || []);
      setCount(data.count || 0);
      setPage(nextPage);
      toast.success(`Loaded ${data.items?.length || 0} job listings!`);
    } catch (err) {
      const errorMsg = err.message || "Unable to load job listings.";
      setError(errorMsg);
      setJobs([]);
      setCount(0);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }

  // ----------------------------
  // 🔹 Fetch Resume Scores (AI)
  // ----------------------------
  useEffect(() => {
    if (!token || !userId || jobs.length === 0) return;

    let cancelled = false;
    (async () => {
      const toScore = jobs.filter(
        (job) => resumeScores[job.source_id] === undefined
      );
      if (toScore.length === 0) return;

      const results = await Promise.all(
        toScore.map(async (job) => {
          try {
            const res = await fetchResumeScore(job.description || "", token);
            return { id: job.source_id, score: res?.score ?? null };
          } catch {
            return { id: job.source_id, score: null };
          }
        })
      );

      if (!cancelled) {
        setResumeScores((prev) => {
          const next = { ...prev };
          results.forEach(({ id, score }) => {
            next[id] = score;
          });
          return next;
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [jobs, token, userId]);

  // ----------------------------
  // 🔹 Handle filters
  // ----------------------------
  function handleInputChange(e) {
    const { name, value, type, checked } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function applyFilters() {
    setResumeScores({});
    loadJobs(1, filters);
  }

  function resetFilters() {
    setFilters(defaultFilters);
    setResumeScores({});
    loadJobs(1, defaultFilters);
    toast.success("Filters reset!");
  }

  // ----------------------------
  // 🔹 Pagination
  // ----------------------------
  function handlePageChange(delta) {
    const nextPage = Math.max(1, page + delta);
    setResumeScores({});
    loadJobs(nextPage, filters);
  }

  // ----------------------------
  // 🔹 Expand/Collapse job desc
  // ----------------------------
  function toggleDescription(jobId) {
    setExpanded((prev) =>
      prev.includes(jobId)
        ? prev.filter((id) => id !== jobId)
        : [...prev, jobId]
    );
  }

  // ----------------------------
  // 🔹 Load saved jobs from DB
  // ----------------------------
  async function loadSavedJobs(userId) {
    try {
      const data = await fetchSavedJobs(userId, token);
      const savedIds = data
        .filter((app) => app.status === "saved")
        .map((app) => app.job_id);
      setSavedJobs(savedIds);
    } catch (err) {
      console.error("Failed to load saved jobs:", err);
      toast.error("Unable to load saved jobs");
    }
  }

  // ----------------------------
  // 🔹 Save a job
  // ----------------------------
  async function handleSaveJob(job) {
    if (!token || !userId) {
      toast.error("Please log in to save jobs!");
      return;
    }

    const jobData = {
      job_id: job.source_id,
      job_title: job.title,
      company: job.company,
      location: job.locations?.[0] || "",
      url: job.url,
    };

    const saveToast = toast.loading("Saving job...");

    try {
      await saveJob(jobData, token);
      setSavedJobs((prev) => [...prev, job.source_id]);
      toast.success("Job saved successfully! ⭐", { id: saveToast });
    } catch (err) {
      console.error("Failed to save job:", err);
      toast.error(err.message || "Failed to save job", { id: saveToast });
    }
  }

  // ----------------------------
  // 🔹 Unsave a job
  // ----------------------------
  async function handleUnsaveJob(jobId) {
    if (!token || !userId) return;

    const unsaveToast = toast.loading("Removing from saved...");

    try {
      await unsaveJob(jobId, token);
      setSavedJobs((prev) => prev.filter((id) => id !== jobId));
      toast.success("Job removed from saved", { id: unsaveToast });
    } catch (err) {
      console.error("Failed to unsave job:", err);
      toast.error(err.message || "Failed to remove job", { id: unsaveToast });
    }
  }

  // ----------------------------
  // 🔹 UI Rendering
  // ----------------------------
  if (loading && jobs.length === 0) {
    return <Loader message="Loading job listings..." />;
  }

  return (
    <div className="page-shell listings-page">
      <header className="page-header">
        <h1>Realtime Job Listings</h1>
        <p>
          Browse current openings fetched directly from Adzuna API. Use filters
          to refine results.
        </p>
      </header>

      {/* Filters */}
      <div className="card-panel filters-panel" role="region" aria-label="Job filters">
        <div className="filters-row">
          <input
            type="search"
            name="what"
            value={filters.what}
            placeholder="🔍 Search for a job title"
            onChange={handleInputChange}
          />
          <input
            type="text"
            name="where"
            value={filters.where}
            placeholder="📍 Location"
            onChange={handleInputChange}
          />
        </div>

        <div className="filters-row">
          <select name="maxDaysOld" value={filters.maxDaysOld} onChange={handleInputChange}>
            <option value="">Date posted</option>
            <option value="1">Within 1 day</option>
            <option value="5">Within 5 days</option>
            <option value="10">Within 10 days</option>
            <option value="30">Within 30 days</option>
          </select>

          <select name="salaryMin" value={filters.salaryMin} onChange={handleInputChange}>
            <option value="">Salary</option>
            <option value="40000">$40,000+</option>
            <option value="60000">$60,000+</option>
            <option value="80000">$80,000+</option>
            <option value="100000">$100,000+</option>
            <option value="120000">$120,000+</option>
            <option value="150000">$150,000+</option>
          </select>

          <select name="workType" value={filters.workType} onChange={handleInputChange}>
            <option value="">Work type</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">In-person</option>
          </select>

          <select name="employmentType" value={filters.employmentType} onChange={handleInputChange}>
            <option value="">Employment type</option>
            <option value="fullTime">Full-time</option>
            <option value="partTime">Part-time</option>
            <option value="contract">Contract</option>
            <option value="temporary">Temporary</option>
          </select>
        </div>

        <div className="filters-row filter-actions">
          <button type="button" className="primary-btn" onClick={applyFilters} disabled={loading}>
            {loading ? "Applying..." : "Apply filters"}
          </button>
          <button type="button" className="ghost-btn" onClick={resetFilters} disabled={loading}>
            Reset
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* ✅ Empty State */}
      {!loading && jobs.length === 0 && !error && (
        <div className="empty-state">
          <h3>No Jobs Found</h3>
          <p>
            Try adjusting your filters or search terms.  
            New job listings appear here in real time! ⚡
          </p>
        </div>
      )}

      {/* Job Results */}
      {jobs.length > 0 && (
        <>
          <div className="listings-meta">
            Showing {jobs.length} results (Page {page})
          </div>

          <div className="job-grid">
            {jobs.map((job) => {
              const expandedDesc = expanded.includes(job.source_id);
              const isSaved = savedJobs.includes(job.source_id);
              const score = resumeScores[job.source_id];

              return (
                <article key={job.source_id} className="job-card">
                  <header>
                    <div className="job-headline">
                      <h2>{job.title}</h2>
                      <span>{job.company || "Unknown company"}</span>
                      {token && score !== undefined && (
                        <div
                          className={`resume-score ${
                            score === null
                              ? ""
                              : score >= 75
                              ? "high"
                              : score >= 50
                              ? "medium"
                              : "low"
                          }`}
                        >
                          Resume Match: {score === null ? "N/A" : `${score}%`}
                        </div>
                      )}
                    </div>
                    {job.salary && job.salary.min && (
                      <div className="comp-range">
                        {job.salary.currency || "USD"} {formatSalary(job.salary.min)}
                        {job.salary.max ? ` – ${formatSalary(job.salary.max)}` : ""}
                      </div>
                    )}
                  </header>

                  <div className="job-meta">
                    {job.locations?.length > 0 && (
                      <span className="badge-chip">{job.locations.join(" · ")}</span>
                    )}
                    {job.work_modes?.length > 0 && (
                      <span className="badge-chip">{job.work_modes.join(" / ")}</span>
                    )}
                    {job.categories?.length > 0 && (
                      <span className="badge-chip">{job.categories.join(", ")}</span>
                    )}
                  </div>

                  {job.description && (
                    <div className="description">
                      {expandedDesc
                        ? job.description
                        : `${job.description.slice(0, 260)}${
                            job.description.length > 260 ? "..." : ""
                          }`}
                      {job.description.length > 260 && (
                        <button
                          type="button"
                          className="toggle-description"
                          onClick={() => toggleDescription(job.source_id)}
                        >
                          {expandedDesc ? "Show less" : "Read more"}
                        </button>
                      )}
                    </div>
                  )}

                  <div className="job-actions">
                    {token && (
                      <button
                        type="button"
                        className={`save-btn ${isSaved ? "saved" : ""}`}
                        onClick={() =>
                          isSaved ? handleUnsaveJob(job.source_id) : handleSaveJob(job)
                        }
                      >
                        {isSaved ? "★ Saved" : "☆ Save"}
                      </button>
                    )}
                    {job.url && (
                      <a
                        className="apply-link"
                        href={job.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Apply now
                      </a>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          <div className="pagination-row">
            <button
              type="button"
              className="ghost-btn"
              onClick={() => handlePageChange(-1)}
              disabled={page === 1 || loading}
            >
              Previous
            </button>
            <span className="page-indicator">Page {page}</span>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => handlePageChange(1)}
              disabled={jobs.length < PAGE_SIZE || loading}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function formatSalary(value) {
  if (!Number.isFinite(value)) return value;
  return value.toLocaleString();
}
