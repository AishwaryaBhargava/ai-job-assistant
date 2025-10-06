import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "./ResumeAnalyzer.css";
import FeedbackButtons from "../components/FeedbackButtons";

const API_BASE_URL = "http://127.0.0.1:8000";

const DIMENSION_LABELS = {
  skills: "Skills",
  experience: "Experience",
  education: "Education",
  keywords: "Keywords",
};

function createBreakdownRows(analysis) {
  return Object.entries(DIMENSION_LABELS).map(([key, label]) => {
    const item = analysis?.breakdown?.[key];
    const applicable = item?.applicable;
    const scoreDisplay = applicable ? `${item.score}%` : "N/A";
    const missingCritical = (item?.missing || []).filter((entry) => entry.critical);
    const missingOther = (item?.missing || []).filter((entry) => !entry.critical);

    let highlight = "All requirements met.";
    if (!item) {
      highlight = "Not evaluated.";
    } else if (!applicable) {
      highlight = "Not specified in job description.";
    } else if (missingCritical.length) {
      highlight = `Critical gaps: ${missingCritical
        .map((entry) => entry.requirement)
        .join(", ")}.`;
    } else if (missingOther.length) {
      highlight = `Consider adding: ${missingOther
        .map((entry) => entry.requirement)
        .join(", ")}.`;
    }

    return {
      key,
      label,
      scoreDisplay,
      highlight,
    };
  });
}

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

function buildAnalysisPreview(analysis) {
  if (!analysis || typeof analysis !== "object") {
    return "Analysis available.";
  }
  const parts = [];
  if (typeof analysis.overall_score === "number") {
    parts.push(`Overall ${analysis.overall_score}%`);
  }
  if (Array.isArray(analysis.suggestions) && analysis.suggestions.length > 0) {
    parts.push(`Suggestions: ${analysis.suggestions.slice(0, 2).join(" | ")}`);
  }
  if (!parts.length) {
    return "Detailed breakdown ready.";
  }
  return parts.join(" - ");
}

export default function ResumeAnalyzer() {
  const [resumeSource, setResumeSource] = useState("text");
  const [resume, setResume] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDesc, setJobDesc] = useState("");
  const [result, setResult] = useState(null);
  const [analysisMeta, setAnalysisMeta] = useState(null);
  const [analysisReady, setAnalysisReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [modalData, setModalData] = useState({ open: false, title: "", mode: "text", payload: null });

  const fileInputRef = useRef(null);
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  const userIdRef = useRef(localStorage.getItem("user_id"));
  const isAuthenticated = Boolean(token);

  useEffect(() => {
    const handleStorage = () => {
      setToken(localStorage.getItem("token"));
      userIdRef.current = localStorage.getItem("user_id");
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
    try {
      const response = await fetch(`${API_BASE_URL}/resume/history`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to load saved analyses.");
      }

      const data = await response.json();
      setHistory(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      toast.error(err.message || "Unable to load analysis history.");
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleSourceChange = (source) => {
    setResumeSource(source);
    setAnalysisReady(false);
    setAnalysisMeta(null);
    if (source === "text") {
      setResumeFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setResumeFile(file);
    setAnalysisReady(false);
    setAnalysisMeta(null);
  };

  const clearFile = () => {
    setResumeFile(null);
    setAnalysisReady(false);
    setAnalysisMeta(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const analyze = async () => {
    const trimmedJobDesc = jobDesc.trim();
    if (!trimmedJobDesc) {
      toast.error("Please provide a job description.");
      return;
    }

    if (resumeSource === "text") {
      if (!resume.trim()) {
        toast.error("Please provide your resume text or switch to the file upload option.");
        return;
      }
    } else if (!resumeFile) {
      toast.error("Please upload a resume file.");
      return;
    }

    setLoading(true);
    setResult(null);
    setAnalysisMeta(null);
    setAnalysisReady(false);

    const authToken = token || localStorage.getItem("token");
    const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};

    try {
      let response;

      if (resumeSource === "file") {
        const formData = new FormData();
        formData.append("job_description", trimmedJobDesc);
        formData.append("file", resumeFile);

        response = await fetch(`${API_BASE_URL}/resume/analyze-file`, {
          method: "POST",
          headers,
          body: formData,
        });
      } else {
        const payload = userIdRef.current
          ? { user_id: userIdRef.current, resume_text: resume }
          : { resume_text: resume };

        response = await fetch(
          `${API_BASE_URL}/resume/analyze?job_description=${encodeURIComponent(trimmedJobDesc)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...headers,
            },
            body: JSON.stringify(payload),
          }
        );
      }

      if (!response.ok) {
        let message = "Analysis failed. Please try again.";
        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      const data = await response.json();
      const analysisPayload = data.analysis_result || data;
      setResult(analysisPayload);
      setAnalysisReady(true);
      toast.success("Analysis completed successfully!");

      setAnalysisMeta({
        resumeSource,
        resumeText: resume,
        jobDescription: trimmedJobDesc,
        resumeFilename: data.resume_filename || (resumeFile ? resumeFile.name : null),
        resumeFile: resumeSource === "file" ? resumeFile : null,
      });
    } catch (err) {
      toast.error(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!isAuthenticated) {
      toast.error("Please log in to save your analysis.");
      return;
    }
    if (!analysisMeta || !result) {
      toast.error("Run an analysis before saving.");
      return;
    }

    if (analysisMeta.resumeSource === "file" && !analysisMeta.resumeFile) {
      toast.error("The resume file is no longer available. Re-upload and analyze before saving.");
      return;
    }

    setSaving(true);

    try {
      const formData = new FormData();
      formData.append("resume_source", analysisMeta.resumeSource);
      formData.append("job_description", analysisMeta.jobDescription);
      formData.append("analysis_result", JSON.stringify(result));

      if (analysisMeta.resumeSource === "text") {
        formData.append("resume_text", analysisMeta.resumeText || "");
      } else if (analysisMeta.resumeFile) {
        const filename = analysisMeta.resumeFilename || analysisMeta.resumeFile.name;
        formData.append("resume_filename", filename);
        formData.append("file", analysisMeta.resumeFile);
      }

      const response = await fetch(`${API_BASE_URL}/resume/history`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        let message = "Failed to save analysis.";
        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      const data = await response.json();
      if (data?.item) {
        setHistory((prev) => [data.item, ...prev]);
      } else {
        fetchHistory();
      }

      toast.success("Analysis saved to your history!");
    } catch (err) {
      toast.error(err.message || "Could not save analysis.");
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (item) => {
    if (!token) {
      toast.error("You must be logged in to download resumes.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/resume/history/${item.id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Session expired. Please log in again.");
        }
        throw new Error("Failed to download resume.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = item.resume_filename || "resume";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Resume downloaded successfully!");
    } catch (err) {
      toast.error(err.message || "Could not download resume.");
    }
  };

  const handleDelete = async (analysisId) => {
    if (!token) {
      toast.error("You must be logged in to delete saved analyses.");
      return;
    }
    const confirmDelete = window.confirm("Delete this saved analysis?");
    if (!confirmDelete) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/resume/history/${analysisId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        let message = "Failed to delete analysis.";
        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      setHistory((prev) => prev.filter((item) => item.id !== analysisId));
      toast.success("Analysis deleted successfully!");
    } catch (err) {
      toast.error(err.message || "Could not delete analysis.");
    }
  };

  const breakdownRows = createBreakdownRows(result);

  const openModal = ({ title, mode = "text", payload = null }) => {
    setModalData({ open: true, title, mode, payload });
  };

  const closeModal = () => {
    setModalData({ open: false, title: "", mode: "text", payload: null });
  };

  const renderModalContent = () => {
    if (modalData.mode === "analysis" && modalData.payload) {
      const modalRows = createBreakdownRows(modalData.payload);
      return (
        <div className="analysis-modal-content">
          <div className="overall-score">
            Overall Alignment: {modalData.payload.overall_score ?? "-"}%
          </div>
          <table className="breakdown-table">
            <thead>
              <tr>
                <th>Dimension</th>
                <th>Score</th>
                <th>Highlights</th>
              </tr>
            </thead>
            <tbody>
              {modalRows.map((row) => (
                <tr key={row.key}>
                  <td>{row.label}</td>
                  <td>{row.scoreDisplay}</td>
                  <td>{row.highlight}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Array.isArray(modalData.payload.suggestions) && modalData.payload.suggestions.length > 0 && (
            <div className="suggestions-block">
              <h4>Next Steps</h4>
              <ul className="suggestions-list">
                {modalData.payload.suggestions.map((suggestion, index) => (
                  <li key={index}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }

    const textContent = typeof modalData.payload === "string" ? modalData.payload : "";
    return <pre className="modal-text-block">{textContent || "-"}</pre>;
  };

  if (historyLoading && history.length === 0) {
    return <Loader message="Loading Resume Analyzer..." />;
  }

  return (
    <div className="analyzer-wrapper">
      <div className="analyzer-container">
        <h2 className="analyzer-title">Resume Analyzer</h2>
        <div className="analyzer-form">
          <div className="resume-source-section">
            <div className="section-title">Provide Your Resume</div>
            <div className="resume-option-grid">
              <button
                type="button"
                className={`option-card ${resumeSource === "text" ? "selected" : ""}`}
                onClick={() => handleSourceChange("text")}
                disabled={loading}
              >
                <div className="option-label">Paste Resume</div>
                <div className="option-helper">Use manual text input</div>
              </button>
              <button
                type="button"
                className={`option-card ${resumeSource === "file" ? "selected" : ""}`}
                onClick={() => handleSourceChange("file")}
                disabled={loading}
              >
                <div className="option-label">Upload File</div>
                <div className="option-helper">PDF, DOC, DOCX, TXT, RTF</div>
              </button>
            </div>
          </div>

          {resumeSource === "text" ? (
            <div className="manual-entry-panel">
              <textarea
                placeholder="Paste your resume text here..."
                value={resume}
                onChange={(e) => {
                  setResume(e.target.value);
                  setAnalysisReady(false);
                  setAnalysisMeta(null);
                }}
                disabled={loading}
              />
              <p className="input-hint">Paste the plain text version of your resume.</p>
            </div>
          ) : (
            <div className="file-upload-panel">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt,.rtf"
                onChange={handleFileChange}
                disabled={loading}
              />
              <p className="input-hint">Supported formats: PDF, DOC, DOCX, TXT, RTF.</p>
              {resumeFile && <p className="selected-file-name">{resumeFile.name}</p>}
              {resumeFile && (
                <button
                  type="button"
                  className="clear-file-btn"
                  onClick={clearFile}
                  disabled={loading}
                >
                  Remove file
                </button>
              )}
            </div>
          )}

          <textarea
            placeholder="Paste the job description here..."
            value={jobDesc}
            onChange={(e) => {
              setJobDesc(e.target.value);
              setAnalysisReady(false);
              setAnalysisMeta(null);
            }}
            disabled={loading}
          />

          <div className="action-row">
            <button className="analyze-btn" onClick={analyze} disabled={loading}>
              {loading ? "Analyzing..." : "Generate Analysis"}
            </button>
            <button
              className="save-btn"
              onClick={handleSave}
              disabled={!analysisReady || saving || !isAuthenticated}
              title={!isAuthenticated ? "Log in to save analyses." : undefined}
            >
              {saving ? "Saving..." : "Save Analysis"}
            </button>
          </div>
        </div>

        {result && (
          <div className="analysis-result">
            <h3>Results</h3>
            <div className="overall-score">Overall Alignment: {result.overall_score}%</div>

            <table className="breakdown-table">
              <thead>
                <tr>
                  <th>Dimension</th>
                  <th>Score</th>
                  <th>Highlights</th>
                </tr>
              </thead>
              <tbody>
                {breakdownRows.map((row) => (
                  <tr key={row.key}>
                    <td>{row.label}</td>
                    <td>{row.scoreDisplay}</td>
                    <td>{row.highlight}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {result.suggestions && result.suggestions.length > 0 && (
              <div className="suggestions-block">
                <h4>Next Steps</h4>
                <ul className="suggestions-list">
                  {result.suggestions.map((suggestion, index) => (
                    <li key={index}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* ✅ AI Feedback Buttons */}
            <div className="feedback-section">
              <h4>Was this AI analysis helpful?</h4>
              <FeedbackButtons
                itemText={result.suggestions?.join(", ") || "No suggestions"}
                source="resume_analyzer"
              />
            </div>
          </div>
        )}

        {isAuthenticated && (
          <div className="history-section">
            <div className="history-header">
              <h3>Saved Analyses</h3>
              <button className="refresh-btn" onClick={fetchHistory} disabled={historyLoading}>
                {historyLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
            {!historyLoading && history.length === 0 && (
              <div className="empty-state">
                <h3>No Saved Analyses Yet</h3>
                <p>Run a resume–job description match above and click <strong>Save Analysis</strong> to keep it here for reference. 📊</p>
              </div>
            )}
            {historyLoading && <div className="loading-state">Loading your saved analyses...</div>}
            {!historyLoading && history.length > 0 && (
              <div className="table-wrapper">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Score</th>
                      <th>Resume</th>
                      <th>Job Description</th>
                      <th>In-depth Analysis</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => {
                      const analysisPreview = buildAnalysisPreview(item.analysis_result);
                      return (
                        <tr key={item.id}>
                          <td>{formatDate(item.created_at)}</td>
                          <td>{item.analysis_result?.overall_score ?? "-"}</td>
                          <td>
                            {item.resume_source === "file" ? (
                              <button
                                type="button"
                                className="link-button"
                                onClick={() => handleDownload(item)}
                              >
                                Download {item.resume_filename || "resume"}
                              </button>
                            ) : (
                              <div className="preview-block">
                                <div className="truncated-text">{item.resume_text || "-"}</div>
                                {item.resume_text && (
                                  <button
                                    type="button"
                                    className="view-more-btn"
                                    onClick={() =>
                                      openModal({
                                        title: "Resume",
                                        mode: "text",
                                        payload: item.resume_text,
                                      })
                                    }
                                  >
                                    View More
                                  </button>
                                )}
                              </div>
                            )}
                          </td>
                          <td>
                            <div className="preview-block">
                              <div className="truncated-text">{item.job_description || "-"}</div>
                              {item.job_description && (
                                <button
                                  type="button"
                                  className="view-more-btn"
                                  onClick={() =>
                                    openModal({
                                      title: "Job Description",
                                      mode: "text",
                                      payload: item.job_description,
                                    })
                                  }
                                >
                                  View More
                                </button>
                              )}
                            </div>
                          </td>
                          <td>
                            <div className="preview-block">
                              <div className="truncated-text">{analysisPreview}</div>
                              {item.analysis_result && (
                                <button
                                  type="button"
                                  className="view-more-btn"
                                  onClick={() =>
                                    openModal({
                                      title: "Analysis Details",
                                      mode: "analysis",
                                      payload: item.analysis_result,
                                    })
                                  }
                                >
                                  View More
                                </button>
                              )}
                            </div>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="delete-btn"
                              onClick={() => handleDelete(item.id)}
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        <div className="global-feedback">
          <p>How would you rate your overall Resume Analyzer experience?</p>
          <FeedbackButtons
            itemText="Resume Analyzer overall experience"
            source="resume_analyzer_overall"
          />
        </div>
      </div>

      {modalData.open && (
        <div className="modal-backdrop" onClick={closeModal}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h4>{modalData.title}</h4>
              <button type="button" className="modal-close-btn" onClick={closeModal}>
                Close
              </button>
            </div>
            <div className="modal-content">
              {renderModalContent()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}