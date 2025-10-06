import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "./ResumeReviewer.css";
import FeedbackButtons from "../components/FeedbackButtons";

const API_BASE_URL = "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const day = new Intl.DateTimeFormat(undefined, { day: "2-digit", month: "long", year: "numeric" }).format(date);
  const tzPart = Intl.DateTimeFormat(undefined, { timeZoneName: "short" })
    .formatToParts(date)
    .find((part) => part.type === "timeZoneName")?.value;
  return tzPart ? `${day} (${tzPart})` : day;
}

function buildReviewPreview(review) {
  if (!review || typeof review !== "object") {
    return "Review available";
  }
  const parts = [];
  if (typeof review.ats_score === "number") {
    parts.push(`ATS ${review.ats_score}`);
  }
  if (Array.isArray(review.quick_fixes) && review.quick_fixes.length > 0) {
    parts.push(`Focus: ${review.quick_fixes[0].title}`);
  }
  if (Array.isArray(review.weak_sections) && review.weak_sections.length > 0) {
    parts.push(`Weak: ${review.weak_sections[0].section}`);
  }
  return parts.join(" | ") || "Detailed feedback ready";
}

function ReviewDetail({ review }) {
  if (!review) {
    return null;
  }

  const renderList = (items, emptyLabel) => {
    if (!Array.isArray(items) || items.length === 0) {
      return <p className="reviewer-empty">{emptyLabel}</p>;
    }
    return (
      <ul className="reviewer-list">
        {items.map((item, index) => {
          const key = `${index}-${item.section || item.title || item.original || "item"}`;
          if (item.section) {
            return (
              <li key={key}>
                <strong>{item.section}:</strong> {item.issue}
                {item.evidence ? <span className="reviewer-evidence"> • {item.evidence}</span> : null}
              </li>
            );
          }
          if (item.original && item.improved) {
            return (
              <li key={key}>
                <div className="reviewer-phrase-original">{item.original}</div>
                <div className="reviewer-phrase-improved">{item.improved}</div>
                {item.reason ? <small>{item.reason}</small> : null}
              </li>
            );
          }
          if (item.title) {
            return (
              <li key={key}>
                <div className="reviewer-quickfix-title">{item.title}</div>
                <div>{item.description}</div>
                <small>Impact: {item.impact} | Effort ~{item.effort_minutes} min</small>
              </li>
            );
          }
          return <li key={key}>{JSON.stringify(item)}</li>;
        })}
      </ul>
    );
  };

  const missing = review.missing_keywords || {};
  const hasMissing = (Array.isArray(missing.must_have) && missing.must_have.length) ||
    (Array.isArray(missing.nice_to_have) && missing.nice_to_have.length);

  return (
    <div className="reviewer-detail">
      <div className="reviewer-score-card">
        <div className="reviewer-score-value">{review.ats_score ?? "-"}</div>
        <div className="reviewer-score-label">ATS Score</div>
        {review.summary_headline ? <p className="reviewer-score-summary">{review.summary_headline}</p> : null}
      </div>

      <div className="reviewer-section">
        <h4>Overall Feedback</h4>
        <p>{review.overall_feedback || "No feedback provided."}</p>
      </div>

      <div className="reviewer-section">
        <h4>Quick Fixes</h4>
        {renderList(review.quick_fixes, "No quick fixes suggested.")}
      </div>

      <div className="reviewer-section">
        <h4>Weak Sections</h4>
        {renderList(review.weak_sections, "No weak sections flagged.")}
      </div>

      <div className="reviewer-section">
        <h4>Phrasing Improvements</h4>
        {renderList(review.phrasing_suggestions, "No phrasing changes recommended.")}
      </div>

      <div className="reviewer-section">
        <h4>Missing Keywords</h4>
        {hasMissing ? (
          <div className="reviewer-keywords">
            {missing.role_family ? <p className="reviewer-subtle">Likely focus: {missing.role_family}</p> : null}
            <div className="reviewer-keyword-block">
              <span className="reviewer-keyword-label">Must have</span>
              <div className="reviewer-pills">
                {(missing.must_have || []).map((item) => (
                  <span className="reviewer-pill" key={`must-${item}`}>{item}</span>
                ))}
              </div>
            </div>
            <div className="reviewer-keyword-block">
              <span className="reviewer-keyword-label">Nice to have</span>
              <div className="reviewer-pills">
                {(missing.nice_to_have || []).map((item) => (
                  <span className="reviewer-pill" key={`nice-${item}`}>{item}</span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="reviewer-empty">No gaps detected.</p>
        )}
      </div>

      {/* ✅ AI Feedback Buttons */}
      <div className="reviewer-section">
        <h4>Was this AI feedback helpful?</h4>
        <FeedbackButtons
          itemText={review.overall_feedback || "No overall feedback"}
          source="resume_reviewer"
        />
      </div>
    </div>
  );
}


export default function ResumeReviewer() {
  const [resumeSource, setResumeSource] = useState("text");
  const [resumeText, setResumeText] = useState("");
  const [resumeFile, setResumeFile] = useState(null);

  const [reviewResult, setReviewResult] = useState(null);
  const [publicSummary, setPublicSummary] = useState(null);
  const [reviewContext, setReviewContext] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(null);
  const [saving, setSaving] = useState(false);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  const [modalData, setModalData] = useState({ open: false, title: "", mode: "text", payload: null });

  const fileInputRef = useRef(null);
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const isAuthenticated = Boolean(token);

  useEffect(() => {
    const handleStorage = () => {
      setToken(localStorage.getItem("token"));
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const fetchHistory = async () => {
    if (!token) {
      setHistory([]);
      return;
    }
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/resume-review/history`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load saved reviews.");
      }

      const data = await response.json();
      setHistory(Array.isArray(data.items) ? data.items : []);
      toast.success("Review history loaded successfully!");
    } catch (err) {
      const errorMsg = err.message || "Unable to load review history.";
      setHistoryError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const resetOutcome = () => {
    setReviewResult(null);
    setPublicSummary(null);
    setReviewContext(null);
    setError(null);
    setSaveError(null);
    setSaveSuccess(null);
  };

  const handleSourceChange = (source) => {
    setResumeSource(source);
    if (source === "text") {
      setResumeFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
    resetOutcome();
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setResumeFile(file);
    setReviewResult(null);
    setPublicSummary(null);
    setReviewContext(null);
    setError(null);
    if (file) {
      toast.success(`File "${file.name}" selected!`);
    }
  };

  const clearFile = () => {
    setResumeFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    toast.success("File cleared");
  };

  const openModal = ({ title, mode, payload }) => {
    setModalData({ open: true, title, mode, payload });
  };

  const closeModal = () => {
    setModalData({ open: false, title: "", mode: "text", payload: null });
  };

  const runReview = async () => {
    if (resumeSource === "text") {
      if (!resumeText.trim()) {
        const errorMsg = "Please provide your resume text or switch to the file upload option.";
        setError(errorMsg);
        toast.error(errorMsg);
        return;
      }
    } else if (!resumeFile) {
      const errorMsg = "Please upload a resume file.";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    setLoading(true);
    setError(null);
    setSaveError(null);
    setSaveSuccess(null);
    setReviewResult(null);
    setPublicSummary(null);
    setReviewContext(null);

    try {
      let response;
      if (resumeSource === "text") {
        response = await fetch(`${API_BASE_URL}/resume-review/review`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ resume_text: resumeText }),
        });
      } else {
        const formData = new FormData();
        formData.append("file", resumeFile);
        response = await fetch(`${API_BASE_URL}/resume-review/review-file`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          body: formData,
        });
      }

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        const message = detail?.detail || detail?.message || "Failed to review resume.";
        throw new Error(message);
      }

      const data = await response.json();

      if (data.review_result) {
        setReviewResult(data.review_result);
        setReviewContext({
          resume_source: data.resume_source || resumeSource,
          resume_text: data.resume_source === "text" ? data.resume_text ?? resumeText : null,
          resume_filename: data.resume_filename || resumeFile?.name || null,
        });
        setPublicSummary(null);
        toast.success("Resume reviewed successfully! 🎉");
      } else {
        setReviewResult(null);
        setPublicSummary(data);
        toast.success("ATS score generated! Log in for full feedback.");
      }
    } catch (err) {
      const errorMsg = err.message || "Something went wrong while reviewing your resume.";
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!reviewResult) {
      const errorMsg = "Nothing to save yet.";
      setSaveError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const formData = new FormData();
      const source = reviewContext?.resume_source || resumeSource;
      formData.append("review_payload", JSON.stringify(reviewResult));
      formData.append("resume_source", source);

      if (source === "text") {
        const textPayload = reviewContext?.resume_text ?? resumeText;
        if (!textPayload || !textPayload.trim()) {
          throw new Error("Resume text is missing; please rerun the review before saving.");
        }
        formData.append("resume_text", textPayload);
      } else {
        const filePayload = resumeFile;
        if (!filePayload) {
          throw new Error("Resume file not available. Please re-upload and review again before saving.");
        }
        formData.append("file", filePayload);
        formData.append("resume_filename", filePayload.name);
      }

      const response = await fetch(`${API_BASE_URL}/resume-review/save`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        const message = detail?.detail || detail?.message || "Failed to save review.";
        throw new Error(message);
      }

      const data = await response.json();
      if (data?.item) {
        setHistory((prev) => [data.item, ...(prev || [])]);
      }
      const successMsg = "Review saved to your history.";
      setSaveSuccess(successMsg);
      toast.success(successMsg);
    } catch (err) {
      const errorMsg = err.message || "Unable to save this review.";
      setSaveError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!id) return;
    const confirmDelete = window.confirm("Delete this saved review?");
    if (!confirmDelete) return;

    try {
      const response = await fetch(`${API_BASE_URL}/resume-review/history/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        const message = detail?.detail || detail?.message || "Failed to delete review.";
        throw new Error(message);
      }

      setHistory((prev) => (prev || []).filter((item) => item.id !== id));
      toast.success("Review deleted successfully!");
    } catch (err) {
      const errorMsg = err.message || "Unable to delete review.";
      setHistoryError(errorMsg);
      toast.error(errorMsg);
    }
  };

  const handleDownload = async (item) => {
    if (!item?.id) return;
    
    const downloadToast = toast.loading("Downloading resume...");
    
    try {
      const response = await fetch(`${API_BASE_URL}/resume-review/history/${item.id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Download failed.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.resume_filename || "resume";
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success("Resume downloaded successfully!", { id: downloadToast });
    } catch (err) {
      const errorMsg = err.message || "Unable to download resume.";
      setHistoryError(errorMsg);
      toast.error(errorMsg, { id: downloadToast });
    }
  };

  const renderModalContent = () => {
    if (modalData.mode === "review") {
      return <ReviewDetail review={modalData.payload} />;
    }
    if (modalData.mode === "json") {
      return <pre className="reviewer-pre">{JSON.stringify(modalData.payload, null, 2)}</pre>;
    }
    return <pre className="reviewer-pre">{modalData.payload}</pre>;
  };

  if (loading) {
    return <Loader message="Analyzing your resume..." />;
  }

  if (historyLoading && history.length === 0) {
    return <Loader message="Loading your review history..." />;
  }

  return (
    <div className="resume-reviewer-page">
      <header className="reviewer-header">
        <h1>Resume Reviewer</h1>
        <p>Instant ATS-style scoring plus recruiter-grade feedback. Log in to unlock full guidance and history.</p>
      </header>

      <div className="reviewer-layout">
        <section className="reviewer-card reviewer-input-card">
          <div className="reviewer-toggle">
            <button
              type="button"
              className={resumeSource === "text" ? "active" : ""}
              onClick={() => handleSourceChange("text")}
            >
              <div className="option-label">Paste Resume Text</div>
              <div className="option-helper">Use manual text input</div>
            </button>
            <button
              type="button"
              className={resumeSource === "file" ? "active" : ""}
              onClick={() => handleSourceChange("file")}
            >
              <div className="option-label">Upload Resume File</div>
              <div className="option-helper">PDF, DOC, DOCX, TXT, RTF</div>
            </button>
          </div>

          {resumeSource === "text" ? (
            <textarea
              className="reviewer-textarea"
              rows={18}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste your resume here..."
            />
          ) : (
            <div className="reviewer-file-panel">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt,.rtf"
                onChange={handleFileChange}
              />
              {resumeFile ? (
                <div className="reviewer-file-info">
                  <span>{resumeFile.name}</span>
                  <button type="button" onClick={clearFile}>Clear</button>
                </div>
              ) : null}
            </div>
          )}

          <button type="button" className="reviewer-primary" onClick={runReview} disabled={loading}>
            {loading ? "Reviewing..." : "Run Review"}
          </button>
          {error ? <p className="reviewer-error">{error}</p> : null}
          {!isAuthenticated ? (
            <p className="reviewer-hint">Create an account or log in to unlock detailed feedback and saving.</p>
          ) : null}
        </section>
      </div>

      <section className="reviewer-card reviewer-result-card">
        <div className="reviewer-result-header">
          <h2>Review Output</h2>
          <p>Run the review to see ATS score, recruiter insights, and priority fixes.</p>
        </div>

        {!publicSummary && !reviewResult ? (
          <div className="reviewer-placeholder">
            <p>Upload your resume above and click <strong>Run Review</strong> to generate results.</p>
          </div>
        ) : null}

        {publicSummary && !reviewResult ? (
            <div className="reviewer-public-summary">
              <div className="reviewer-score-card">
                <div className="reviewer-score-value">{publicSummary.ats_score ?? "-"}</div>
                <div className="reviewer-score-label">ATS Score</div>
              </div>
              <p>{publicSummary.summary_headline || "Sign up to see the full feedback breakdown."}</p>
            </div>
          ) : null}

          {reviewResult ? <ReviewDetail review={reviewResult} /> : null}

          {isAuthenticated && reviewResult ? (
            <div className="reviewer-save-block">
              <button type="button" className="reviewer-secondary" onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save to History"}
              </button>
              {saveError ? <p className="reviewer-error">{saveError}</p> : null}
              {saveSuccess ? <p className="reviewer-success">{saveSuccess}</p> : null}
            </div>
          ) : null}
        </section>

      {isAuthenticated ? (
        <section className="reviewer-history">
          <div className="reviewer-history-header">
            <h2>Saved Reviews</h2>
            <button type="button" onClick={fetchHistory} className="reviewer-link" disabled={historyLoading}>
              {historyLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {historyError ? <p className="reviewer-error">{historyError}</p> : null}

          {!historyLoading && history.length === 0 && (
            <div className="empty-state">
              <h3>No Reviews Found</h3>
              <p>Run a resume review above, then save it to see it listed here. 💾</p>
            </div>
          )}

          {!historyLoading && history.length > 0 ? (
            <div className="reviewer-table-wrapper">
              <table className="reviewer-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>ATS</th>
                    <th>Summary</th>
                    <th>Quick Fixes</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => {
                    const review = item.review_result;
                    const quickFixTitles = Array.isArray(item.quick_fix_titles) && item.quick_fix_titles.length
                      ? item.quick_fix_titles.join(", ")
                      : (Array.isArray(review?.quick_fixes) && review.quick_fixes.length
                        ? review.quick_fixes.map((fix) => fix.title).join(", ")
                        : "-");
                    return (
                      <tr key={item.id}>
                        <td>{formatDate(item.created_at)}</td>
                        <td>{item.ats_score_cache ?? review?.ats_score ?? "-"}</td>
                        <td>
                          <div className="reviewer-preview">
                            <div className="reviewer-preview-text">{buildReviewPreview(review)}</div>
                            <button
                              type="button"
                              className="reviewer-link"
                              onClick={() => openModal({ title: "Full Review", mode: "review", payload: review })}
                            >
                              View
                            </button>
                          </div>
                        </td>
                        <td>{quickFixTitles || "-"}</td>
                        <td>
                          <div className="reviewer-actions">
                            {item.resume_source === "file" ? (
                              <button type="button" className="reviewer-link" onClick={() => handleDownload(item)}>Download</button>
                            ) : (
                              <button
                                type="button"
                                className="reviewer-link"
                                onClick={() => openModal({ title: "Resume Text", mode: "text", payload: item.resume_text || "-" })}
                              >
                                View Resume
                              </button>
                            )}
                            <button
                              type="button"
                              className="reviewer-link danger"
                              onClick={() => handleDelete(item.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      {reviewResult && (
        <div className="reviewer-global-feedback">
          <p>Did this overall review meet your expectations?</p>
          <FeedbackButtons
            itemText={reviewResult.summary_headline || "General review"}
            source="resume_reviewer_overall"
          />
        </div>
      )}

      {modalData.open ? (
        <div className="reviewer-modal-backdrop" onClick={closeModal}>
          <div className="reviewer-modal" onClick={(event) => event.stopPropagation()}>
            <div className="reviewer-modal-header">
              <h4>{modalData.title}</h4>
              <button type="button" className="reviewer-close" onClick={closeModal}>×</button>
            </div>
            <div className="reviewer-modal-content">{renderModalContent()}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}