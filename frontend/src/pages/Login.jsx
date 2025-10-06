// src/pages/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import Loader from "../components/Loader";
import "./Login.css";
import API_BASE from "../services/apiClient";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user_id", data.user_id);
        window.dispatchEvent(new Event("auth-change"));

        toast.success("Login successful! 🎉");
        navigate("/");
      } else {
        toast.error(data.detail || "Invalid email or password");
      }
    } catch (error) {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      {loading ? (
        <Loader message="Signing you in..." />
      ) : (
        <>
          <div className="login-welcome">
            <h1>👋 Welcome Back!</h1>
            <p>Sign in to continue your AI Job Assistant journey</p>
          </div>

          <div className="login-container">
            <h2 className="login-title">Login</h2>
            <form className="login-form" onSubmit={handleLogin}>
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button type="submit" className="login-btn">
                Login
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}

export default Login;
