import { useEffect, useMemo, useState } from "react";
import { fetchPreferences, persistPreferences } from "../services/preferencesService";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "./PageLayout.css";
import "./JobPreferences.css";

const DRAFT_STORAGE_KEY = "job_prefs_draft_v1";
const GUEST_STORAGE_KEY = "job_prefs_guest_v1";

const DEFAULT_FORM = {
  values: [],
  role_families: [],
  specializations: [],
  locations: [],
  remote_ok: true,
  seniority_levels: [],
  leadership_preference: "none",
  company_sizes: [],
  industries_like: [],
  industries_avoid: [],
  skills: [],
  disliked_skills: [],
  min_salary: 0,
  currency: "USD",
  job_search_status: "actively_looking",
};

const VALUE_OPTIONS = [
  "Impactful work",
  "Learning & growth",
  "Inclusive culture",
  "Work-life balance",
  "Ownership & autonomy",
  "Mentorship",
  "Compensation",
  "Mission alignment",
  "Innovation speed",
];

const ROLE_FAMILY_OPTIONS = [
  "Software Engineering",
  "AI & Machine Learning",
  "Data & Analytics",
  "Product Management",
  "Design & UX",
  "DevOps & Infrastructure",
  "Growth & Marketing",
  "Sales & Customer Success",
  "Operations",
  "People & HR",
];

const SPECIALIZATION_OPTIONS = [
  "Large Language Models",
  "Applied Machine Learning",
  "Computer Vision",
  "Conversational AI",
  "MLOps",
  "Backend Engineering",
  "Frontend Engineering",
  "Full Stack",
  "Product Discovery",
  "Product Strategy",
  "UX Research",
];

const LOCATION_OPTIONS = [
  "Remote - Global",
  "Remote - USA",
  "New York, USA",
  "San Francisco Bay Area, USA",
  "Austin, USA",
  "Seattle, USA",
  "Toronto, Canada",
  "Vancouver, Canada",
  "London, UK",
  "Berlin, Germany",
];

const SENIORITY_OPTIONS = [
  { id: "internship", label: "Internship" },
  { id: "entry", label: "Entry / New Grad" },
  { id: "junior", label: "Junior (1-2 yrs)" },
  { id: "mid", label: "Mid-level (3-5 yrs)" },
  { id: "senior", label: "Senior (6-8 yrs)" },
  { id: "lead", label: "Lead / Manager" },
  { id: "executive", label: "Executive" },
];

const COMPANY_SIZE_OPTIONS = [
  "1-10 employees",
  "11-50 employees",
  "51-200 employees",
  "201-500 employees",
  "501-1,000 employees",
  "1,001-5,000 employees",
  "5,001-10,000 employees",
  "10,000+ employees",
];

const INDUSTRY_OPTIONS = [
  "Artificial Intelligence",
  "Developer Tools",
  "Enterprise Software",
  "Fintech",
  "Healthcare",
  "Biotech",
  "Climate & Sustainability",
  "E-commerce",
  "Gaming",
  "Media & Entertainment",
  "Robotics",
  "Cybersecurity",
  "Education",
  "Government / Public Sector",
];

const SKILL_OPTIONS = [
  "Python",
  "JavaScript",
  "TypeScript",
  "React",
  "Node.js",
  "SQL",
  "NoSQL",
  "TensorFlow",
  "PyTorch",
  "AWS",
  "Azure",
  "GCP",
  "Product Discovery",
  "User Research",
  "Data Storytelling",
  "People Management",
];

const JOB_STATUS_OPTIONS = [
  { id: "actively_looking", label: "Actively looking" },
  { id: "open_to_offers", label: "Open to offers" },
  { id: "not_looking", label: "Not looking" },
];

const steps = [
  { id: "values", title: "Role Priorities", subtitle: "Select up to three" },
  { id: "roles", title: "Roles & Focus", subtitle: "Pick the work you enjoy" },
  { id: "locations", title: "Locations", subtitle: "Where do you want to work?" },
  { id: "experience", title: "Experience", subtitle: "Level and leadership" },
  { id: "company", title: "Company Fit", subtitle: "Size and industries" },
  { id: "skills", title: "Skills", subtitle: "Highlight strengths" },
  { id: "summary", title: "Summary", subtitle: "Review and save" },
];

function nextState(list, value, limit) {
  const existing = new Set(list);
  if (existing.has(value)) {
    existing.delete(value);
    return Array.from(existing);
  }
  if (limit && existing.size >= limit) {
    return Array.from(existing);
  }
  existing.add(value);
  return Array.from(existing);
}

function classNames(base, condition) {
  return condition ? `${base} selected` : base;
}

export default function JobPreferences() {

  const token = localStorage.getItem("token");
  const isAuthed = Boolean(token);

  const [form, setForm] = useState(DEFAULT_FORM);
  const [currentStep, setCurrentStep] = useState(0);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [customLocation, setCustomLocation] = useState("");
  const [customSkill, setCustomSkill] = useState("");
  const [customAvoidSkill, setCustomAvoidSkill] = useState("");

  useEffect(() => {
    async function bootstrap() {
      try {
        if (isAuthed) {
          const data = await fetchPreferences();
          setForm((prev) => ({ ...prev, ...data }));
          localStorage.removeItem(DRAFT_STORAGE_KEY);
          toast.success("Preferences loaded successfully! 📋");
        } else {
          const stored = localStorage.getItem(GUEST_STORAGE_KEY) || localStorage.getItem(DRAFT_STORAGE_KEY);
          if (stored) {
            const parsed = JSON.parse(stored);
            setForm((prev) => ({ ...prev, ...parsed }));
            toast.success("Draft preferences restored! 💾");
          }
        }
      } catch (error) {
        // swallow 404 (no preferences set)
        if (error.message && !error.message.includes("404")) {
          toast.error("Failed to load preferences. Starting fresh.");
        }
      } finally {
        setInitializing(false);
      }
    }

    bootstrap();
  }, [isAuthed]);

  useEffect(() => {
    if (initializing || isAuthed) return;
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(form));
  }, [form, initializing, isAuthed]);

  const stepProgress = ((currentStep + 1) / steps.length) * 100;

  function goToStep(index) {
    if (index >= 0 && index < steps.length) {
      setCurrentStep(index);
    }
  }

  function handleToggle(field, value, limit) {
    setForm((prev) => ({
      ...prev,
      [field]: nextState(prev[field], value, limit),
    }));
  }

  function handleRadio(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleInput(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function addCustom(field, valueSetter, value) {
    const trimmed = value.trim();
    if (!trimmed) return;
    setForm((prev) => {
      if (prev[field].includes(trimmed)) return prev;
      return {
        ...prev,
        [field]: [...prev[field], trimmed],
      };
    });
    valueSetter("");
    toast.success(`Added "${trimmed}" ✨`);
  }

  function removeItem(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field].filter((item) => item !== value),
    }));
    toast.success(`Removed "${value}"`);
  }

  function validateStep(stepId) {
    switch (stepId) {
      case "values":
        return form.values.length > 0;
      case "roles":
        return form.role_families.length > 0;
      case "locations":
        return form.remote_ok || form.locations.length > 0;
      default:
        return true;
    }
  }

  async function handleSubmit() {
    setStatus(null);
    if (!validateStep("summary")) return;

    if (isAuthed) {
      try {
        setLoading(true);
        await persistPreferences(form);
        setStatus({ type: "success", message: "Preferences saved." });
        toast.success("Preferences saved successfully! 🎉");
      } catch (error) {
        setStatus({ type: "error", message: error.message || "Failed to save preferences." });
        toast.error(error.message || "Failed to save preferences. Please try again.");
      } finally {
        setLoading(false);
      }
    } else {
      const payload = {
        ...form,
        updated_at: new Date().toISOString(),
      };
      localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(payload));
      setStatus({
        type: "success",
        message: "Preferences stored in this browser. Create an account to keep them across devices.",
      });
      toast.success("Preferences saved locally! 💾");
    }
  }

  function handleNext() {
    const step = steps[currentStep];
    if (!validateStep(step.id)) {
      setStatus({ type: "error", message: "Please complete the required choices before continuing." });
      toast.error("Please complete the required choices before continuing.");
      return;
    }
    setStatus(null);
    goToStep(currentStep + 1);
  }

  function handleBack() {
    setStatus(null);
    goToStep(currentStep - 1);
  }

  const summary = useMemo(() => ({
    values: form.values,
    role_families: form.role_families,
    specializations: form.specializations,
    locations: form.locations,
    remote_ok: form.remote_ok,
    seniority_levels: form.seniority_levels,
    leadership_preference: form.leadership_preference,
    company_sizes: form.company_sizes,
    industries_like: form.industries_like,
    industries_avoid: form.industries_avoid,
    skills: form.skills,
    disliked_skills: form.disliked_skills,
    min_salary: form.min_salary,
    currency: form.currency,
    job_search_status: form.job_search_status,
  }), [form]);

  const isLastStep = currentStep === steps.length - 1;

  if (initializing) {
    return (
      <div className="page-shell preferences-page">
        <Loader message="Loading your preferences..." />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-shell preferences-page">
        <Loader message="Saving your preferences..." />
      </div>
    );
  }

  return (
    <div className="page-shell preferences-page">
      <header className="page-header">
        <h1>Shape Your Ideal Opportunity</h1>
        <p className="header-description">
          Tell us what matters most so we can recommend roles that match your goals. You can update these preferences at any time.
        </p>
      </header>

      <div className="wizard-shell">
        <div className="wizard-progress" aria-label="Progress">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`wizard-step ${index === currentStep ? "active" : ""} ${index < currentStep ? "done" : ""}`}
            >
              <span className="step-number">Step {index + 1}</span>
              <strong className="step-title">{step.title}</strong>
            </div>
          ))}
        </div>

        <div className="card-panel">
          <div className="step-hint">Progress {Math.round(stepProgress)}%</div>
          <div className="wizard-body">
            {renderStep({
              step: steps[currentStep],
              form,
              handleToggle,
              handleRadio,
              handleInput,
              addCustom,
              removeItem,
              customLocation,
              setCustomLocation,
              customSkill,
              setCustomSkill,
              customAvoidSkill,
              setCustomAvoidSkill,
            })}
          </div>
        </div>

        {status && (
          <div className={`status-banner ${status.type === "error" ? "error" : ""}`}>
            <span className="status-message">{status.message}</span>
          </div>
        )}

        <div className="wizard-actions">
          <button
            type="button"
            className="secondary-btn"
            onClick={handleBack}
            disabled={currentStep === 0}
          >
            Back
          </button>
          {!isLastStep ? (
            <button type="button" className="primary-btn" onClick={handleNext}>
              Next
            </button>
          ) : (
            <button
              type="button"
              className="primary-btn"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? "Saving..." : isAuthed ? "Save Preferences" : "Finish"}
            </button>
          )}
        </div>
      </div>

      {isLastStep && (
        <div className="summary-card" aria-live="polite">
          <SummarySection title="Priorities" items={summary.values} fallback="No priorities selected." />
          <SummarySection
            title="Preferred roles"
            items={[...summary.role_families, ...summary.specializations]}
            fallback="Pick at least one role focus."
          />
          <SummarySection
            title="Location preferences"
            items={summary.remote_ok ? ["Remote OK", ...summary.locations] : summary.locations}
            fallback="Let us know if remote is OK or choose a location."
          />
          <SummarySection
            title="Experience"
            items={[
              summary.seniority_levels.join(", ") || null,
              summary.leadership_preference !== "none" ? `Leadership: ${summary.leadership_preference}` : null,
            ].filter(Boolean)}
            fallback="No experience preferences yet."
          />
          <SummarySection
            title="Company preferences"
            items={[...summary.company_sizes, ...summary.industries_like]}
            fallback="Company size or industries will help narrow matches."
          />
          <SummarySection
            title="Industries to avoid"
            items={summary.industries_avoid}
            fallback="No exclusions set."
          />
          <SummarySection
            title="Skills to highlight"
            items={summary.skills}
            fallback="Add skills so we can match you more accurately."
          />
          <SummarySection
            title="Skills to downplay"
            items={summary.disliked_skills}
            fallback="No filtered skills."
          />
          <SummarySection
            title="Compensation & status"
            items={[`Minimum salary: ${summary.currency} ${summary.min_salary || 0}`, `Search status: ${summary.job_search_status}`]}
            fallback="Set a salary floor and job search status."
          />
        </div>
      )}
    </div>
  );
}

function renderStep(args) {
  const {
    step,
    form,
    handleToggle,
    handleRadio,
    handleInput,
    addCustom,
    removeItem,
    customLocation,
    setCustomLocation,
    customSkill,
    setCustomSkill,
    customAvoidSkill,
    setCustomAvoidSkill,
  } = args;

  switch (step.id) {
    case "values":
      return (
        <fieldset className="preference-group">
          <legend className="preference-legend">What excites you about your next role?</legend>
          <p className="inline-note">Select up to three priorities.</p>
          <div className="pill-grid">
            {VALUE_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                className={classNames("pill", form.values.includes(option))}
                onClick={() => handleToggle("values", option, 3)}
              >
                {option}
              </button>
            ))}
          </div>
        </fieldset>
      );

    case "roles":
      return (
        <div className="multi-column">
          <fieldset className="preference-group">
            <legend className="preference-legend">Role families (pick up to five)</legend>
            <div className="pill-grid">
              {ROLE_FAMILY_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.role_families.includes(option))}
                  onClick={() => handleToggle("role_families", option, 5)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="preference-group">
            <legend className="preference-legend">Specializations (optional, up to five)</legend>
            <div className="pill-grid">
              {SPECIALIZATION_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.specializations.includes(option))}
                  onClick={() => handleToggle("specializations", option, 5)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
      );

    case "locations":
      return (
        <div className="multi-column">
          <fieldset className="preference-group">
            <legend className="preference-legend">Locations</legend>
            <label className="inline-toggle">
              <input
                type="checkbox"
                checked={form.remote_ok}
                onChange={(event) => handleInput("remote_ok", event.target.checked)}
              />
              Open to remote roles
            </label>
            <div className="pill-grid">
              {LOCATION_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.locations.includes(option))}
                  onClick={() => handleToggle("locations", option)}
                >
                  {option}
                </button>
              ))}
            </div>
            <div className="input-row">
              <input
                type="text"
                className="text-input"
                placeholder="Add another city or region"
                value={customLocation}
                onChange={(event) => setCustomLocation(event.target.value)}
              />
              <button
                type="button"
                className="ghost-btn"
                onClick={() => addCustom("locations", setCustomLocation, customLocation)}
              >
                Add
              </button>
            </div>
            {form.locations.length > 0 && (
              <div className="quick-stat" aria-live="polite">
                {form.locations.map((location) => (
                  <span key={location} className="badge-chip">
                    {location}
                    <button type="button" className="toggle-description" onClick={() => removeItem("locations", location)}>
                      Remove
                    </button>
                  </span>
                ))}
              </div>
            )}
          </fieldset>
        </div>
      );

    case "experience":
      return (
        <div className="multi-column">
          <fieldset className="preference-group">
            <legend className="preference-legend">Experience level (up to two)</legend>
            <div className="pill-grid">
              {SENIORITY_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={classNames("pill", form.seniority_levels.includes(option.id))}
                  onClick={() => handleToggle("seniority_levels", option.id, 2)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="preference-group">
            <legend className="preference-legend">Leadership preference</legend>
            <div className="pill-grid">
              {["none", "individual_contributor", "manager"].map((value) => (
                <button
                  key={value}
                  type="button"
                  className={classNames("pill", form.leadership_preference === value)}
                  onClick={() => handleRadio("leadership_preference", value)}
                >
                  {value === "none" ? "No preference" : value === "manager" ? "Manager" : "Individual contributor"}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
      );

    case "company":
      return (
        <div className="multi-column">
          <fieldset className="preference-group">
            <legend className="preference-legend">Ideal company size</legend>
            <div className="pill-grid">
              {COMPANY_SIZE_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.company_sizes.includes(option))}
                  onClick={() => handleToggle("company_sizes", option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="preference-group">
            <legend className="preference-legend">Industries</legend>
            <div className="pill-grid">
              {INDUSTRY_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.industries_like.includes(option))}
                  onClick={() => handleToggle("industries_like", option)}
                >
                  {option}
                </button>
              ))}
            </div>
            <p className="inline-note">Click again to unselect.</p>
            <h4 className="subsection-title">Industries to avoid</h4>
            <div className="pill-grid">
              {INDUSTRY_OPTIONS.map((option) => (
                <button
                  key={`${option}-avoid`}
                  type="button"
                  className={classNames("pill", form.industries_avoid.includes(option))}
                  onClick={() => handleToggle("industries_avoid", option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
      );

    case "skills":
      return (
        <div className="multi-column">
          <fieldset className="preference-group">
            <legend className="preference-legend">Skills to highlight</legend>
            <div className="pill-grid">
              {SKILL_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={classNames("pill", form.skills.includes(option))}
                  onClick={() => handleToggle("skills", option)}
                >
                  {option}
                </button>
              ))}
            </div>
            <div className="input-row">
              <input
                type="text"
                className="text-input"
                placeholder="Add another skill"
                value={customSkill}
                onChange={(event) => setCustomSkill(event.target.value)}
              />
              <button
                type="button"
                className="ghost-btn"
                onClick={() => addCustom("skills", setCustomSkill, customSkill)}
              >
                Add
              </button>
            </div>
          </fieldset>

          <fieldset className="preference-group">
            <legend className="preference-legend">Skills to downplay</legend>
            <div className="pill-grid">
              {form.skills.map((skill) => (
                <button
                  key={`${skill}-avoid`}
                  type="button"
                  className={classNames("pill", form.disliked_skills.includes(skill))}
                  onClick={() => handleToggle("disliked_skills", skill)}
                >
                  {skill}
                </button>
              ))}
            </div>
            <div className="input-row">
              <input
                type="text"
                className="text-input"
                placeholder="Add skill to avoid"
                value={customAvoidSkill}
                onChange={(event) => setCustomAvoidSkill(event.target.value)}
              />
              <button
                type="button"
                className="ghost-btn"
                onClick={() => addCustom("disliked_skills", setCustomAvoidSkill, customAvoidSkill)}
              >
                Add
              </button>
            </div>
          </fieldset>
        </div>
      );

    case "summary":
      return (
        <fieldset className="preference-group">
          <legend className="preference-legend">Final details</legend>
          <div className="multi-column">
            <div className="form-field">
              <label htmlFor="min-salary" className="section-label">Minimum salary</label>
              <div className="input-row">
                <select
                  className="select-input"
                  value={form.currency}
                  onChange={(event) => handleInput("currency", event.target.value)}
                >
                  <option value="USD">USD</option>
                  <option value="CAD">CAD</option>
                  <option value="GBP">GBP</option>
                  <option value="EUR">EUR</option>
                  <option value="INR">INR</option>
                </select>
                <input
                  id="min-salary"
                  type="number"
                  className="text-input"
                  min="0"
                  value={form.min_salary}
                  onChange={(event) => handleInput("min_salary", Number(event.target.value))}
                />
              </div>
            </div>
            <div className="form-field">
              <label className="section-label">Job search status</label>
              <div className="pill-grid">
                {JOB_STATUS_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={classNames("pill", form.job_search_status === option.id)}
                    onClick={() => handleRadio("job_search_status", option.id)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </fieldset>
      );

    default:
      return null;
  }
}

function SummarySection({ title, items, fallback }) {
  const hasItems = Array.isArray(items) && items.length > 0;
  return (
    <div className="summary-section">
      <h3 className="summary-title">{title}</h3>
      {hasItems ? (
        <ul className="summary-list">
          {items.map((item) => (
            <li key={`${title}-${item}`} className="summary-item">{item}</li>
          ))}
        </ul>
      ) : (
        <p className="inline-note">{fallback}</p>
      )}
    </div>
  );
}