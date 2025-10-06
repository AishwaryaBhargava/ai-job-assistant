// src/components/Footer.jsx
import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <p>© {new Date().getFullYear()} AI Job Assistant. All rights reserved.</p>
      </div>
    </footer>
  );
}
