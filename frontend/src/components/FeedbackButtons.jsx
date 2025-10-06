// src/components/FeedbackButtons.jsx
import { useState } from "react";
import { toast } from "react-hot-toast";
import "./FeedbackButtons.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function FeedbackButtons({ itemText, source }) {
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem("token");
  const userId = localStorage.getItem("user_id");

  // If no logged-in user, don't show anything
  if (!token) return null;

  const sendFeedback = async (type) => {
    if (loading || selected) return;
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/feedback/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          item_text: itemText || "No content",
          feedback_type: type,
          source: source || "general",
          user_id: userId,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to send feedback");
      }

      setSelected(type);
      toast.success("✅ Thanks for your feedback!");
    } catch (error) {
      console.error("Feedback error:", error);
      toast.error("Could not send feedback.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback-buttons">
      <button
        className={`feedback-btn up ${selected === "up" ? "selected" : ""}`}
        onClick={() => sendFeedback("up")}
        disabled={loading || selected !== null}
        aria-label="Like"
        title="Helpful"
      >
        👍
      </button>
      <button
        className={`feedback-btn down ${selected === "down" ? "selected" : ""}`}
        onClick={() => sendFeedback("down")}
        disabled={loading || selected !== null}
        aria-label="Dislike"
        title="Needs improvement"
      >
        👎
      </button>
    </div>
  );
}
