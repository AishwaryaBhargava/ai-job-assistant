// src/components/Toast.jsx
import { Toaster } from "react-hot-toast";
import "./Toast.css";

export default function Toast() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 3000,
        style: {
          background: "var(--toast-bg, #1e1e1e)",
          color: "var(--toast-text, #f5f5f5)",
          border: "1px solid var(--toast-border, #2d2d2d)",
          borderRadius: "10px",
          padding: "10px 16px",
        },
        success: {
          iconTheme: { primary: "#10b981", secondary: "#fff" },
        },
        error: {
          iconTheme: { primary: "#ef4444", secondary: "#fff" },
        },
      }}
    />
  );
}
