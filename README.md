# 🧠 AI Job Assistant  
**Your personalized AI-powered career companion — bridging resumes, jobs, and intelligence.**

[![Frontend – Vercel](https://img.shields.io/badge/Frontend-Live-brightgreen?logo=vercel)](https://ai-job-assistant-henna.vercel.app/)
[![Backend – Render](https://img.shields.io/badge/Backend-Active-blue?logo=render)](https://ai-job-assistant-i7tg.onrender.com)

---

## 🏗️ System Architecture

```text
                          ┌────────────────────────────┐
                          │        User Browser        │
                          │ (AI Job Assistant Website) │
                          └──────────────┬─────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────────────────────┐
                         │         Vercel Frontend (React + Vite)        │
                         │   https://ai-job-assistant-henna.vercel.app   │
                         └─────────────────┬─────────────────────────────┘
                                           │ Fetch API Requests
                                           ▼
                      ┌─────────────────────────────────────────────────┐
                      │          Render Backend (FastAPI + Python)      │
                      │     https://ai-job-assistant-i7tg.onrender.com  │
                      └─────────────────┬───────────────────────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
   ┌────────────────┐        ┌────────────────────────┐   ┌────────────────────┐
   │ MongoDB Atlas  │        │ Azure OpenAI (GPT-4o)  │   │ Adzuna Job API     │
   │ (User Data,    │        │ Resume Analysis, AI    │   │ Real-time Listings │
   │ Preferences)   │        │ Suggestions)           │   │                    │
   └────────────────┘        └────────────────────────┘   └────────────────────┘
````

---

## 🌟 Overview

**AI Job Assistant** is a full-stack web platform designed to revolutionize how candidates prepare and apply for jobs.
It brings together **AI-driven resume analysis**, **smart recommendations**, and **real-time job data** — helping users tailor applications and track their job search journey in one place.

Key components:

* 🎯 AI-powered **Resume Reviewer**
* 🔍 Real-time **Job Search & Tracking**
* 🧠 **Personalized Recommendations**
* 🔐 **Authentication & User Management**
* 💬 Feedback & Continuous Learning System

---

## 🚀 Live Demo

* 🖥 **Frontend (Vercel):** [ai-job-assistant-henna.vercel.app](https://ai-job-assistant-henna.vercel.app/)
* ⚙️ **Backend (Render):** [ai-job-assistant-i7tg.onrender.com](https://ai-job-assistant-i7tg.onrender.com)
* 💾 **API Docs:** [Swagger UI](https://ai-job-assistant-i7tg.onrender.com/docs)

---

## 🧩 Features

### 🧠 Resume Analyzer & Reviewer

Upload or paste your resume to receive instant **ATS-style scoring** and **AI-generated feedback** on keywords, structure, and optimization tips.

### 💼 Job Listings

Fetch **real-time jobs** from the Adzuna API with filters for location, salary, remote work, and role type.

### 🧭 Job Preferences

Save and update your preferences to refine personalized job recommendations.

### 🧾 Application Tracker

Log your job applications, monitor their status, and record notes or interview progress.

### 🔐 Authentication

Secure **JWT-based login** and registration with persistent sessions.

### 💬 Feedback System

Capture user feedback for ongoing improvement and AI fine-tuning.

---

## 🧱 Folder Structure

```text
ai-job-assistant/
│
├── backend/
│   ├── data/
│   │   └── locations.csv
│   │
│   ├── logs/
│   │   ├── ai_job_assistant.log
│   │   └── ai_job_assistant.log.2025-10-05
│   │
│   ├── models/
│   │   ├── application.py
│   │   ├── job.py
│   │   ├── preferences.py
│   │   ├── resume.py
│   │   ├── review.py
│   │   └── user.py
│   │
│   ├── routes/
│   │   ├── answers.py
│   │   ├── applications.py
│   │   ├── auth.py
│   │   ├── feedback.py
│   │   ├── jobs.py
│   │   ├── preferences.py
│   │   ├── profile.py
│   │   ├── recommendations.py
│   │   ├── resume_upload.py
│   │   ├── resume.py
│   │   ├── review.py
│   │   ├── saved_jobs.py
│   │   └── users.py
│   │
│   ├── scripts/
│   │   └── load_locations.py
│   │
│   ├── services/
│   │   ├── scrapers/
│   │   │   ├── html_extractor.py
│   │   │   └── job_scraper.py
│   │   ├── ai_service.py
│   │   ├── job_ingest_service.py
│   │   ├── job_monitor.py
│   │   ├── location_service.py
│   │   ├── parser_service.py
│   │   ├── recommendation_service.py
│   │   └── resume_fit_service.py
│   │
│   ├── uploads/
│   │   └── resumes/
│   │
│   ├── utils/
│   │   └── logger.py
│   │
│   ├── .env
│   ├── auth_utils.py
│   ├── database.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── .env
└── README.md
```

---

## ⚙️ Setup Guide

### 1️⃣ Clone Repository

```bash
git clone https://github.com/AishwaryaBhargava/ai-job-assistant.git
cd ai-job-assistant
```

### 2️⃣ Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

📍 Visit: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3️⃣ Frontend Setup

```bash
cd ../frontend
npm install
npm run dev
```

📍 Visit: [http://localhost:5173](http://localhost:5173)

### 4️⃣ Environment Variables

#### `/frontend/.env`

```bash
VITE_API_BASE_URL=https://ai-job-assistant-i7tg.onrender.com
```

#### `/backend/.env`

```bash
MONGO_URI=your_mongodb_connection_string
DB_NAME=ai_job_assistant
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_AI_DEPLOYMENT=gpt-4o-mini
```

---

## 🧠 API Endpoints Overview

| Endpoint                     | Description                 |
| ---------------------------- | --------------------------- |
| `/auth/register`             | Register a new user         |
| `/auth/login`                | Login and receive JWT token |
| `/resume-review/review-file` | Upload and analyze resume   |
| `/resume-review/review-text` | Analyze pasted resume text  |
| `/applications`              | Manage job applications     |
| `/jobs/search`               | Fetch job listings          |
| `/recommendations`           | Get AI-based job matches    |
| `/feedback`                  | Submit or view feedback     |
| `/health`                    | Backend health check        |

---

## 💬 Future Enhancements

* 🔑 **Forgot Password (reset flow)**
* ✉️ **Email verification at signup**
* 📍 **Fix location autocomplete in Job Preferences**
* ⚙️ **Dynamic Job Preferences** → smarter job matches from user profiles
* 👥 **User roles:** Admin, Applicant, Recruiter

  * Map current users → Applicant
  * Define routes, permissions, and dashboards
* 🧠 **Capture free-text user feedback** and use it to fine-tune AI prompts/models

---

## 📸 Screenshots *(Coming Soon)*

| Home Page                | Resume Reviewer                  |
| ------------------------ | -------------------------------- |
| ![Home](assets/home.png) | ![Reviewer](assets/reviewer.png) |

---

## 🧰 Tech Stack Summary

| Category            | Tools                                          |
| ------------------- | ---------------------------------------------- |
| **Frontend**        | React, Vite, Tailwind CSS, React Router, Toast |
| **Backend**         | FastAPI, Python, Uvicorn                       |
| **Database**        | MongoDB Atlas                                  |
| **AI Engine**       | Azure OpenAI (GPT-4o-mini, Embeddings)         |
| **Job Data Source** | Adzuna API                                     |
| **Hosting**         | Vercel (Frontend), Render (Backend)            |
| **Auth & Security** | JWT Tokens, CORS Middleware                    |
| **Version Control** | Git + GitHub                                   |

---

## 👩‍💻 Author

**Aishwarya Bhargava**
🎓 Master of Science in Information Science @ University of Pittsburgh
🌍 [Portfolio](https://aishwaryabhargava.github.io/portfolio/) • [LinkedIn](https://www.linkedin.com/in/aishwarya-bhargava05/) • [GitHub](https://github.com/AishwaryaBhargava)

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

⭐ *If you like this project, don’t forget to give it a star on GitHub!*
