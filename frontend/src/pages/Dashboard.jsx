import { useEffect, useState } from "react";
import DatePicker from "react-datepicker";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "react-datepicker/dist/react-datepicker.css";
import "./Dashboard.css";
import API_BASE from "../services/apiClient";

export default function Dashboard() {
  const USER_ID = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");

  const [apps, setApps] = useState([]);
  const [form, setForm] = useState({
    job_title: "",
    company: "",
    url: "",
    status: "submitted",
    applied_on: new Date(),
    next_action: "",
    comments: "",
  });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const formatDate = (date) => {
    if (!date) return "-";
    return new Date(date).toLocaleDateString("en-US", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const load = async () => {
    if (!token) {
      toast.error("You must be logged in to see applications.");
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/applications/${USER_ID}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setApps(
        (data || []).map((a) => ({
          ...a,
          edit_status: a.status,
          edit_next_action: a.next_action || "",
          edit_comments:
            Array.isArray(a.comments) && a.comments.length > 0
              ? a.comments[a.comments.length - 1].text
              : "",
          edit_applied_on: a.applied_on ? new Date(a.applied_on) : null,
        }))
      );
    } catch (error) {
      console.error("Load failed:", error);
      toast.error("Error loading applications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveRow = async (app) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/applications/${app._id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: app.edit_status,
          next_action: app.edit_next_action,
          applied_on: app.edit_applied_on
            ? app.edit_applied_on.toISOString()
            : null,
          comments: [
            {
              text: app.edit_comments,
              timestamp: new Date().toISOString(),
            },
          ],
          last_updated: new Date().toISOString(),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Failed to update application");
        return;
      }

      toast.success("Row updated successfully! ✅");
      load();
    } catch (error) {
      console.error("Update failed:", error);
      toast.error("Error updating application");
    } finally {
      setActionLoading(false);
    }
  };

  const deleteRow = async (appId) => {
    if (!window.confirm("Are you sure you want to delete this application?"))
      return;
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/applications/${appId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Failed to delete application");
        return;
      }

      toast.success("Application deleted successfully! 🗑️");
      load();
    } catch (error) {
      console.error("Delete failed:", error);
      toast.error("Error deleting application");
    } finally {
      setActionLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const add = async () => {
    setActionLoading(true);
    try {
      const payload = {
        user_id: USER_ID,
        ...form,
        applied_on: form.applied_on.toISOString(),
        comments: form.comments
          ? [{ text: form.comments, timestamp: new Date().toISOString() }]
          : [],
      };

      const res = await fetch(`${API_BASE}/applications/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || "Failed to add application");
        return;
      }

      toast.success("Application added successfully! 🎉");
      setForm({
        job_title: "",
        company: "",
        url: "",
        status: "submitted",
        applied_on: new Date(),
        next_action: "",
        comments: "",
      });
      load();
    } catch (error) {
      console.error("Add failed:", error);
      toast.error("Error adding application");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <Loader message="Loading your applications..." />;
  }

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">📂 Job Applications Dashboard</h1>

      {/* Add Form */}
      <div className="dashboard-card">
        <h3 className="form-title">Add Application</h3>
        <div className="dashboard-form">
          <input
            name="job_title"
            placeholder="Job Title"
            value={form.job_title}
            onChange={handleChange}
          />
          <input
            name="company"
            placeholder="Company"
            value={form.company}
            onChange={handleChange}
          />
          <input
            name="url"
            placeholder="Job URL"
            value={form.url}
            onChange={handleChange}
          />
          <select name="status" value={form.status} onChange={handleChange}>
            <option value="submitted">Submitted</option>
            <option value="interview">Interview</option>
            <option value="offer">Offer</option>
            <option value="rejected">Rejected</option>
          </select>
          <DatePicker
            selected={form.applied_on}
            onChange={(date) => setForm((f) => ({ ...f, applied_on: date }))}
            dateFormat="dd-MMM-yyyy"
            className="date-picker"
          />
          <input
            name="next_action"
            placeholder="Next Action"
            value={form.next_action}
            onChange={handleChange}
          />
          <textarea
            name="comments"
            placeholder="Comments"
            value={form.comments}
            onChange={handleChange}
          />
          <button className="btn-add" onClick={add} disabled={actionLoading}>
            {actionLoading ? "Adding..." : "Add"}
          </button>
        </div>
      </div>

      {/* Empty State */}
      {!loading && apps.length === 0 && (
        <div className="empty-state">
          <h3>No Applications Yet</h3>
          <p>
            You haven’t added any job applications yet.  
            Start by adding one using the form above! 🚀
          </p>
        </div>
      )}

      {/* Applications Table */}
      {apps.length > 0 && (
        <table className="dashboard-table">
          <thead>
            <tr>
              <th>Job Title</th>
              <th>Company</th>
              <th>URL</th>
              <th>Status</th>
              <th>Applied On</th>
              <th>Next Action</th>
              <th>Comments</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((a, i) => (
              <tr key={i}>
                <td>{a.job_title}</td>
                <td>{a.company}</td>
                <td>
                  {a.url ? (
                    <a href={a.url} target="_blank" rel="noreferrer">
                      Link
                    </a>
                  ) : (
                    "-"
                  )}
                </td>
                <td>
                  {a.isEditing ? (
                    <select
                      className={`status-select ${a.edit_status}`}
                      value={a.edit_status}
                      onChange={(e) =>
                        setApps((prev) =>
                          prev.map((x) =>
                            x._id === a._id
                              ? { ...x, edit_status: e.target.value }
                              : x
                          )
                        )
                      }
                    >
                      <option value="submitted">Submitted</option>
                      <option value="interview">Interview</option>
                      <option value="offer">Offer</option>
                      <option value="rejected">Rejected</option>
                      <option value="saved">Saved</option>
                    </select>
                  ) : (
                    <span className={`badge ${a.status}`}>{a.status}</span>
                  )}
                </td>
                <td>
                  {a.isEditing ? (
                    <DatePicker
                      selected={a.edit_applied_on}
                      onChange={(date) =>
                        setApps((prev) =>
                          prev.map((x) =>
                            x._id === a._id
                              ? { ...x, edit_applied_on: date }
                              : x
                          )
                        )
                      }
                      dateFormat="dd-MMM-yyyy"
                      className="date-picker"
                    />
                  ) : a.applied_on ? (
                    formatDate(a.applied_on)
                  ) : (
                    "-"
                  )}
                </td>
                <td>
                  {a.isEditing ? (
                    <input
                      value={a.edit_next_action}
                      onChange={(e) =>
                        setApps((prev) =>
                          prev.map((x) =>
                            x._id === a._id
                              ? { ...x, edit_next_action: e.target.value }
                              : x
                          )
                        )
                      }
                    />
                  ) : (
                    a.next_action || "-"
                  )}
                </td>
                <td>
                  {a.isEditing ? (
                    <input
                      value={a.edit_comments}
                      onChange={(e) =>
                        setApps((prev) =>
                          prev.map((x) =>
                            x._id === a._id
                              ? { ...x, edit_comments: e.target.value }
                              : x
                          )
                        )
                      }
                    />
                  ) : Array.isArray(a.comments) && a.comments.length > 0 ? (
                    a.comments[a.comments.length - 1].text
                  ) : (
                    "-"
                  )}
                </td>
                <td>{a.last_updated ? formatDate(a.last_updated) : "-"}</td>
                <td>
                  {a.isEditing ? (
                    <div className="btn-group">
                      <button
                        className="btn-save"
                        onClick={() => saveRow(a)}
                        disabled={actionLoading}
                      >
                        {actionLoading ? "Saving..." : "💾 Save"}
                      </button>
                      <button
                        className="btn-delete"
                        onClick={() => deleteRow(a._id)}
                        disabled={actionLoading}
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  ) : (
                    <button
                      className="btn-edit"
                      onClick={() =>
                        setApps((prev) =>
                          prev.map((x) =>
                            x._id === a._id ? { ...x, isEditing: true } : x
                          )
                        )
                      }
                    >
                      ✏️ Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
