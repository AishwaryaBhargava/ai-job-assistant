import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import "./Navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const [isAuthed, setIsAuthed] = useState(Boolean(localStorage.getItem("token")));
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");

  // Initialize theme on mount
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Sync navbar with token changes in same tab
  useEffect(() => {
    const checkAuth = () => setIsAuthed(Boolean(localStorage.getItem("token")));
    window.addEventListener("storage", checkAuth);
    window.addEventListener("auth-change", checkAuth);
    return () => {
      window.removeEventListener("storage", checkAuth);
      window.removeEventListener("auth-change", checkAuth);
    };
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    setIsAuthed(false);
    navigate("/login");
    window.dispatchEvent(new Event("auth-change"));
  };

  const toggleTheme = () => setTheme(prev => (prev === "dark" ? "light" : "dark"));

  const linkClass = ({ isActive }) => (isActive ? "nav__link active" : "nav__link");

  return (
    <nav className="nav">
      <div className="nav__inner">
        <div className="nav__brand">
          <NavLink to="/" className="nav__brandLink">
            AI Job Assistant
          </NavLink>
        </div>

        <ul className="nav__links">
          <li><NavLink to="/" className={linkClass}>Home</NavLink></li>
          <li><NavLink to="/resume" className={linkClass}>Resume Analyzer</NavLink></li>
          <li><NavLink to="/resume-review" className={linkClass}>Resume Reviewer</NavLink></li>
          <li><NavLink to="/jobs" className={linkClass}>Job Listings</NavLink></li>
          <li><NavLink to="/preferences" className={linkClass}>Job Preferences</NavLink></li>

          {isAuthed ? (
            <>
              <li><NavLink to="/profile" className={linkClass}>Profile</NavLink></li>
              <li><NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink></li>
              <li><button className="nav__logout" onClick={logout}>Logout</button></li>
            </>
          ) : (
            <>
              <li><NavLink to="/login" className={linkClass}>Login</NavLink></li>
              <li><NavLink to="/register" className={linkClass}>Register</NavLink></li>
            </>
          )}

          {/* 🌗 Theme Toggle Button */}
          <li>
            <button className="theme-toggle" onClick={toggleTheme}>
              {theme === "dark" ? "🌙" : "☀️"}
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
}
