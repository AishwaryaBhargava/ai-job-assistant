import { Link } from "react-router-dom";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay } from "swiper/modules";
import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";
import "./Home.css";

export default function Home() {
  return (
    <div className="home-container">
      {/* Hero Section */}
      <section className="hero">
        <h1 className="hero-title">AI Job Assistant</h1>
        <p className="hero-subtitle">Your AI-powered career companion</p>
        <div className="hero-description">
          <p>
            Finding the right job in today’s competitive market can be overwhelming. Our AI Job Assistance platform is designed to simplify and enhance your job search journey by bringing together powerful tools and insights in one place. Whether you are preparing your resume, tailoring it for a specific role, or practicing for interviews, our goal is to give you the confidence and resources to stand out.
          </p>
          <h2 className="hero-section-heading">✨ Features & Capabilities</h2>
          <p>
            The platform offers an AI-powered Resume Analyzer, which not only evaluates your resume against job descriptions but also provides actionable suggestions for improvement. With our Job Matching tool, you can discover opportunities that align closely with your skills and career aspirations. The website also includes Interview Prep modules, offering personalized Q&A practice, feedback, and guidance on how to structure your answers effectively.
          </p>
          <p>
            Beyond that, users will benefit from Career Insights—resources that highlight industry trends, in-demand skills, and role-specific advice—helping you make informed decisions about your career path.
          </p>
          <h2 className="hero-section-heading">👥 Who It’s For</h2>
          <p>
            This platform is built for students, recent graduates, and professionals who are actively seeking internships, full-time roles, or career transitions. Whether you are applying to your first job or aiming to pivot into a new field, our tools are designed to adapt to your stage of the journey.
          </p>
          <h2 className="hero-section-heading">🚀 How It Helps</h2>
          <p>
            By combining advanced AI with practical career strategies, this platform acts as your personal career coach—helping you save time, improve your application materials, and boost your chances of landing interviews. Instead of second-guessing whether your resume fits a role or if your interview prep is enough, you’ll have tailored, data-backed feedback guiding you every step of the way.
          </p>
          <div className="hero-cta">
            <a href="/login" className="btn-get-started">🚀 Get Started</a>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <h2 className="section-title">✨ Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <h3>📊 Resume Analyzer</h3>
            <p>
              Upload your resume and a job description, and get a detailed AI-powered match score along with personalized
              suggestions to improve your chances of landing the role.
            </p>
          </div>
          <div className="feature-card">
            <h3>📝 Profile Autofill</h3>
            <p>
              Save time by uploading your resume file. Our system extracts key details and autofills your profile, making
              it easier to apply for jobs quickly.
            </p>
          </div>
          <div className="feature-card">
            <h3>📂 Job Tracking</h3>
            <p>
              Keep track of all your job applications in one place. Update statuses, add next steps, and write notes to
              stay organized throughout your job search.
            </p>
          </div>
          <div className="feature-card">
            <h3>🤖 AI Interview Help</h3>
            <p>
              Get tailored AI-generated answers to common and role-specific interview questions. Practice smarter and
              improve your confidence before interviews.
            </p>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="testimonials">
        <h2 className="section-title">💬 What Our Users Say</h2>
        <Swiper
          modules={[Navigation, Pagination, Autoplay]}
          spaceBetween={20}
          slidesPerView={3}
          loop={true}
          autoplay={{ delay: 3000 }}
          pagination={{ clickable: true }}
          navigation
        >
          {[
            {
              name: "Jessica L.",
              text: "AI Job Assistant completely transformed my job search. Within minutes, I had my resume analyzed against multiple job descriptions, and the personalized suggestions helped me land more interviews than ever before.",
            },
            {
              name: "David R.",
              text: "I’ve always struggled to track my job applications, but the job tracker feature keeps me on top of everything. I know exactly which companies I applied to, what stage I’m at, and what my next steps are.",
            },
            {
              name: "Sophia K.",
              text: "The resume autofill tool saved me hours of manual work. Uploading my resume instantly populated my profile, and I could focus on applying rather than retyping everything.",
            },
            {
              name: "Michael B.",
              text: "The AI interview prep is a game-changer. I practiced answers tailored to my role and felt confident in my interviews. I even got an offer from my top choice company!",
            },
            {
              name: "Emily S.",
              text: "I love how simple yet powerful AI Job Assistant is. It feels like having a personal career coach available 24/7. Highly recommend it to anyone serious about their career growth.",
            },
            {
              name: "Arjun M.",
              text: "The combination of resume analysis, job tracking, and interview prep is brilliant. It gives me a complete system to manage my career journey instead of juggling multiple apps.",
            },
          ].map((t, i) => (
            <SwiperSlide key={i}>
              <div className="testimonial-card">
                <p>"{t.text}"</p>
                <span>- {t.name}</span>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </section>
    </div>
  );
}
