import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Toast from "./components/Toast";

// Components
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";
import ResumeReviewer from "./pages/ResumeReviewer";
import Dashboard from "./pages/Dashboard";
import JobPreferences from "./pages/JobPreferences";
import JobListings from "./pages/JobListings";

function App() {
  return (
    <Router>
      <Navbar />
      <Toast />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/resume" element={<ResumeAnalyzer />} />
        <Route path="/resume-review" element={<ResumeReviewer />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/preferences" element={<JobPreferences />} />
        <Route path="/jobs" element={<JobListings />} />
      </Routes>
      <Footer />
    </Router>
  );
}

export default App;




