// src/pages/Profile.jsx
import { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "./Profile.css";
import API_BASE from "../services/apiClient";

export default function Profile() {
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    phone: "",
    linkedin: "",
    github: "",
    twitter: "",
    portfolio: "",
    location: "",
    websites: [],
    last_resume: "",
    last_resume_name: "",
    last_resume_url: "",
    skills: [],
    education: [{ degree: "", school: "", year: "", gpa: "" }],
    work_experience: [
      { company: "", role: "", duration: "", location: "", tasks: "" },
    ],
  });
  const [resumeFile, setResumeFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);

  const safeDecode = (value) => {
    if (!value) return value;
    try {
      return decodeURIComponent(value);
    } catch (err) {
      // Value isn't URI encoded; fall back to the original string.
      return value;
    }
  };

  // ✅ Skills text for easy editing
  const normalizeResumePath = (rawPath) => {
    if (!rawPath) return "";
    const value = rawPath.trim();
    if (!value) return "";
    if (value.startsWith("http")) return value;
    if (value.startsWith("/profile/resumes/")) return value;
    if (value.startsWith("/resumes/")) return "/profile" + value;
    const parts = value.split(/[\\/]+/).filter(Boolean);
    const filename = parts.length ? parts[parts.length - 1] : "";
    return filename ? "/profile/resumes/" + filename : value;
  };

  const [skillsText, setSkillsText] = useState("");


  // 🔹 Fetch latest profile when component mounts
  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        setPageLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/profile/`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();
        if (!res.ok) {
          console.error("Failed to fetch profile:", data);
          toast.error("Failed to load profile");
          setPageLoading(false);
          return;
        }
        if (!data || data.message === "No profile found") {
          setPageLoading(false);
          return;
        }

        const resumeRawPath = data.last_resume || "";
        const resumePath = normalizeResumePath(data.last_resume_url || resumeRawPath);
        let resumeName = data.last_resume_name;
        if (!resumeName && resumePath) {
          const rawName = resumePath.split("/").pop() || "";
          resumeName = rawName.includes("_")
            ? rawName.slice(rawName.indexOf("_") + 1)
            : rawName;
        }
        resumeName = safeDecode(resumeName);

        setProfile((p) => ({
          ...p,
          ...data,
          last_resume: resumeRawPath || p.last_resume,
          last_resume_url: resumePath || p.last_resume_url,
          last_resume_name: resumeName || safeDecode(p.last_resume_name),
          education: data.education?.length
            ? data.education
            : [{ degree: "", school: "", year: "", gpa: "" }],
          work_experience: data.work_experience?.length
            ? data.work_experience
            : [
                {
                  company: "",
                  role: "",
                  duration: "",
                  location: "",
                  tasks: "",
                },
              ],
        }));
      } catch (err) {
        console.error("Failed to fetch profile:", err);
        toast.error("Error loading profile");
      } finally {
        setPageLoading(false);
      }
    };

    fetchProfile();
  }, []);

  // ✅ Keep skillsText synced
  useEffect(() => {
    setSkillsText(profile.skills.join(", "));
  }, [profile.skills]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile((p) => ({ ...p, [name]: value }));
  };

  // ✅ Upload resume & autofill
  const handleUpload = async () => {
    if (!resumeFile) {
      toast.error("Please upload a PDF or DOCX resume.");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("You must be logged in to upload a resume.");
      return;
    }

    setLoading(true);
    try {
      const parseForm = new FormData();
      parseForm.append("file", resumeFile);

      const parseRes = await fetch(`${API_BASE}/resume-upload/upload`, {
        method: "POST",
        headers: { Authorization: 'Bearer ' + token },
        body: parseForm,
      });

      const parseBody = await parseRes.json().catch(() => ({}));
      if (!parseRes.ok) {
        toast.error(parseBody.detail || "Resume parsing failed on server.");
        return;
      }

      let finalResumeUrl = "";
      let finalResumeRaw = "";
      let finalResumeName = resumeFile.name || "";
      try {
        const storeForm = new FormData();
        storeForm.append("file", resumeFile);
        const storeRes = await fetch(`${API_BASE}/profile/upload-resume`, {
          method: "POST",
          headers: { Authorization: 'Bearer ' + token },
          body: storeForm,
        });
        const storeBody = await storeRes.json().catch(() => ({}));
        if (storeRes.ok) {
          finalResumeRaw = storeBody.file_path || finalResumeRaw;
          finalResumeUrl = storeBody.file_url || storeBody.file_path || "";
          finalResumeName =
            storeBody.original_filename || finalResumeName;
        } else {
          console.warn("Resume file save failed:", storeBody);
        }
      } catch (fileErr) {
        console.warn("Resume file save error:", fileErr);
      }

      const parsed = parseBody?.parsed || {};
      const parsedEducation =
        Array.isArray(parsed.education) && parsed.education.length
          ? parsed.education
          : undefined;
      const parsedWork =
        Array.isArray(parsed.work_experience) && parsed.work_experience.length
          ? parsed.work_experience.map((exp) => ({
              ...exp,
              tasks: Array.isArray(exp?.tasks)
                ? exp.tasks.join(", ")
                : exp?.tasks || "",
            }))
          : undefined;

      setProfile((p) => ({
        ...p,
        name: parsed.name ?? p.name,
        email: parsed.email ?? p.email,
        phone: parsed.phone ?? p.phone,
        linkedin: parsed.linkedin ?? p.linkedin,
        github: parsed.github ?? p.github,
        twitter: parsed.twitter ?? p.twitter,
        portfolio: parsed.portfolio ?? p.portfolio,
        location: parsed.location ?? p.location,
        websites:
          Array.isArray(parsed.websites) && parsed.websites.length
            ? parsed.websites
            : p.websites,
        skills:
          Array.isArray(parsed.skills) && parsed.skills.length
            ? parsed.skills
            : p.skills,
        education: parsedEducation || p.education,
        work_experience: parsedWork || p.work_experience,
        last_resume: finalResumeRaw || p.last_resume,
        last_resume_url:
          normalizeResumePath(finalResumeUrl || finalResumeRaw) || p.last_resume_url,
        last_resume_name:
          safeDecode(finalResumeName) || safeDecode(p.last_resume_name),
      }));

      toast.success("Resume uploaded & parsed successfully! 🎉");
    } catch (err) {
      console.error("Upload failed:", err);
      toast.error("Unexpected error during upload. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadResume = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");
    const normalizedPath = normalizeResumePath(
      profile.last_resume_url || profile.last_resume
    );
    if (!normalizedPath) {
      toast.error("No resume available to download.");
      return;
    }

    const resumePath = normalizedPath.startsWith("http")
      ? normalizedPath
      : `${API_BASE}` +
        (normalizedPath.startsWith("/") ? normalizedPath : "/" + normalizedPath);

    try {
      const headers = token ? { Authorization: "Bearer " + token } : {};
      const res = await fetch(resumePath, { headers });
      if (!res.ok) {
        toast.error("Could not download resume.");
        return;
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const fallbackName = normalizedPath.split("/").pop() || "resume";
      const downloadName = safeDecode(profile.last_resume_name || fallbackName) || "resume";
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Resume downloaded successfully! 📥");
    } catch (err) {
      console.error("Download failed:", err);
      toast.error("Failed to download resume. Please try again.");
    }
  };

  // ✅ Delete resume
  const handleDeleteResume = async () => {
    if (!profile.last_resume && !profile.last_resume_url) return;
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(`${API_BASE}/profile/delete-resume`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        toast.success("Resume deleted successfully! 🗑️");
        setProfile((p) => ({ ...p, last_resume: "", last_resume_name: "", last_resume_url: "" }));
      } else {
        toast.error(data.detail || "Failed to delete resume.");
      }
    } catch (err) {
      console.error("Delete failed:", err);
      toast.error("Error deleting resume. Please try again.");
    }
  };  

  // ✅ Validation
  const validateProfile = () => {
    if (!profile.name.trim()) {
      toast.error("Name is required.");
      return false;
    }
    if (!profile.email.trim()) {
      toast.error("Email is required.");
      return false;
    }

    for (let edu of profile.education) {
      if (
        Object.values(edu).some((f) => f.trim() !== "") &&
        (!edu.degree || !edu.school || !edu.year || !edu.gpa)
      ) {
        toast.error("All fields in each Education entry must be filled.");
        return false;
      }
    }

    for (let exp of profile.work_experience) {
      if (
        Object.values(exp).some((f) => f.trim() !== "") &&
        (!exp.company || !exp.role || !exp.duration || !exp.location || !exp.tasks)
      ) {
        toast.error("All fields in each Work Experience entry must be filled.");
        return false;
      }
    }

    return true;
  };

  // ✅ Save profile
  const handleSave = async () => {
    if (!validateProfile()) return;

    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("You must be logged in to save your profile.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/profile/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...profile,
          skills: skillsText
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s !== ""),
        }),
      });

      const data = await res.json();
      if (res.ok) {
        toast.success(data.message || "Profile saved successfully! ✅");
      } else {
        toast.error(data.detail || "Failed to save profile.");
      }
    } catch (err) {
      console.error("Save failed:", err);
      toast.error("Error saving profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // ✅ Clear all fields
  const handleClear = () => {
    setProfile({
      name: "",
      email: "",
      phone: "",
      linkedin: "",
      github: "",
      twitter: "",
      portfolio: "",
      location: "",
      websites: [],
      last_resume: "",
      last_resume_name: "",
      last_resume_url: "",
      skills: [],
      education: [{ degree: "", school: "", year: "", gpa: "" }],
      work_experience: [
        { company: "", role: "", duration: "", location: "", tasks: "" },
      ],
    });
    setSkillsText("");
    toast.success("All fields cleared!");
  };

  // ✅ Add/remove Education
  const addEducation = () =>
    setProfile((p) => ({
      ...p,
      education: [
        ...p.education,
        { degree: "", school: "", year: "", gpa: "" },
      ],
    }));

  const removeEducation = (i) =>
    setProfile((p) => ({
      ...p,
      education: p.education.filter((_, idx) => idx !== i),
    }));

  // ✅ Add/remove Work Experience
  const addWorkExperience = () =>
    setProfile((p) => ({
      ...p,
      work_experience: [
        ...p.work_experience,
        { company: "", role: "", duration: "", location: "", tasks: "" },
      ],
    }));

  const removeWorkExperience = (i) =>
    setProfile((p) => ({
      ...p,
      work_experience: p.work_experience.filter((_, idx) => idx !== i),
    }));

  if (pageLoading) {
    return <Loader message="Loading your profile..." />;
  }

  return (
    <div className="container profile-container">
      <h2>Profile</h2>

      {/* Resume Upload */}
      <div className="card">
        <h3>Upload Resume</h3>
        {(profile.last_resume || profile.last_resume_url) && (
          <p>
            Last Uploaded: {" "}
            <a href="#" onClick={handleDownloadResume}>
              {
                profile.last_resume_name ||
                normalizeResumePath(profile.last_resume_url || profile.last_resume)
                  .split("/")
                  .pop() ||
                "Resume"
              }
            </a>
            <button className="btn small danger" onClick={handleDeleteResume}>
              Delete
            </button>
          </p>
        )}
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setResumeFile(e.target.files[0])}
        />
        <button className="btn" onClick={handleUpload} disabled={loading}>
          {loading ? "Parsing Resume..." : "Upload & Autofill"}
        </button>
      </div>

      {/* Profile Form */}
      <div className="card">
        <label>Name</label>
        <input name="name" value={profile.name} onChange={handleChange} />

        <label>Email</label>
        <input name="email" value={profile.email} onChange={handleChange} />

        <label>Phone</label>
        <input name="phone" value={profile.phone || ""} onChange={handleChange} />

        <label>Location</label>
        <input
          name="location"
          value={profile.location || ""}
          onChange={handleChange}
        />

        <label>LinkedIn</label>
        <input
          name="linkedin"
          value={profile.linkedin || ""}
          onChange={handleChange}
        />

        <label>GitHub</label>
        <input
          name="github"
          value={profile.github || ""}
          onChange={handleChange}
        />

        <label>Twitter / X</label>
        <input
          name="twitter"
          value={profile.twitter || ""}
          onChange={handleChange}
        />

        <label>Portfolio</label>
        <input
          name="portfolio"
          value={profile.portfolio || ""}
          onChange={handleChange}
        />

        <label>Additional Websites (comma separated)</label>
        <input
          name="websites"
          value={profile.websites?.join(", ") || ""}
          onChange={(e) =>
            setProfile((p) => ({
              ...p,
              websites: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter((s) => s !== ""),
            }))
          }
        />

        <label>Skills (comma separated)</label>
        <input
          name="skills"
          value={skillsText}
          onChange={(e) => setSkillsText(e.target.value)}
          onBlur={() =>
            setProfile((p) => ({
              ...p,
              skills: skillsText
                .split(",")
                .map((s) => s.trim())
                .filter((s) => s !== ""),
            }))
          }
        />

        {/* Education Section */}
        <h3>Education</h3>
        {profile.education.map((edu, i) => (
          <div key={i} className="card small">
            <input
              placeholder="Degree"
              value={edu.degree || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newEdu = [...p.education];
                  newEdu[i].degree = e.target.value;
                  return { ...p, education: newEdu };
                })
              }
            />
            <input
              placeholder="School"
              value={edu.school || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newEdu = [...p.education];
                  newEdu[i].school = e.target.value;
                  return { ...p, education: newEdu };
                })
              }
            />
            <input
              placeholder="Year"
              value={edu.year || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newEdu = [...p.education];
                  newEdu[i].year = e.target.value;
                  return { ...p, education: newEdu };
                })
              }
            />
            <input
              placeholder="GPA"
              value={edu.gpa || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newEdu = [...p.education];
                  newEdu[i].gpa = e.target.value;
                  return { ...p, education: newEdu };
                })
              }
            />
            <button
              className="btn small danger"
              onClick={() => removeEducation(i)}
            >
              Remove
            </button>
          </div>
        ))}
        <button className="btn small" onClick={addEducation}>
          + Add Education
        </button>

        {/* Work Experience Section */}
        <h3>Work Experience</h3>
        {profile.work_experience.map((exp, i) => (
          <div key={i} className="card small">
            <input
              placeholder="Company"
              value={exp.company || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newExp = [...p.work_experience];
                  newExp[i].company = e.target.value;
                  return { ...p, work_experience: newExp };
                })
              }
            />
            <input
              placeholder="Role"
              value={exp.role || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newExp = [...p.work_experience];
                  newExp[i].role = e.target.value;
                  return { ...p, work_experience: newExp };
                })
              }
            />
            <input
              placeholder="Duration"
              value={exp.duration || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newExp = [...p.work_experience];
                  newExp[i].duration = e.target.value;
                  return { ...p, work_experience: newExp };
                })
              }
            />
            <input
              placeholder="Location"
              value={exp.location || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newExp = [...p.work_experience];
                  newExp[i].location = e.target.value;
                  return { ...p, work_experience: newExp };
                })
              }
            />
            <textarea
              placeholder="Tasks (comma separated)"
              value={exp.tasks || ""}
              onChange={(e) =>
                setProfile((p) => {
                  const newExp = [...p.work_experience];
                  newExp[i].tasks = e.target.value;
                  return { ...p, work_experience: newExp };
                })
              }
            />
            <button
              className="btn small danger"
              onClick={() => removeWorkExperience(i)}
            >
              Remove
            </button>
          </div>
        ))}
        <button className="btn small" onClick={addWorkExperience}>
          + Add Work Experience
        </button>
      </div>

      <button className="btn save-profile" onClick={handleSave} disabled={loading}>
        {loading ? "Saving..." : "Save Profile"}
      </button>
      <button className="btn danger" onClick={handleClear}>
        Clear All
      </button>
    </div>
  );
}