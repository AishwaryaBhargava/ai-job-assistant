from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import logger  # ✅ Logger import

from services.job_monitor import start_job_monitor, stop_job_monitor
from routes import (
    answers,
    applications,
    auth,
    jobs,
    preferences,
    profile,
    recommendations,
    resume,
    resume_upload,
    review,
    users,
    saved_jobs,
    feedback,
)

# --- App Initialization ---
logger.info("Initializing FastAPI application: AI-Job-Assistant Backend")
app = FastAPI(title="AI-Job-Assistant Backend")


# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error occurred: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )


# --- CORS Configuration ---
logger.info("Configuring CORS middleware for frontend access")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware successfully configured")


# --- Route Registration ---
logger.info("Registering API routers...")

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(resume.router, prefix="/resume", tags=["Resume"])
app.include_router(review.router, prefix="/resume-review", tags=["Resume Review"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])
app.include_router(answers.router, prefix="/answers", tags=["Answers"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(resume_upload.router, prefix="/resume-upload", tags=["Resume Upload"])
app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(saved_jobs.router, prefix="/saved-jobs", tags=["Saved Jobs"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])

logger.info("All routers registered successfully")


# --- Lifecycle Events ---
@app.on_event("startup")
async def _on_startup() -> None:
    logger.info("🚀 Starting AI-Job-Assistant backend services...")
    try:
        start_job_monitor()
        logger.info("Job monitor started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    logger.info("🛑 Shutting down AI-Job-Assistant backend services...")
    try:
        await stop_job_monitor()
        logger.info("Job monitor stopped successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# --- Basic Routes ---
@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "AI-Job-Assistant Backend is running dYs?"}


@app.get("/health")
def health():
    logger.info("Health check endpoint hit")
    return {"status": "healthy"}


@app.get("/version")
def version():
    logger.info("Version endpoint hit")
    return {"status": "success", "version": "v1.0.0"}


logger.info("✅ FastAPI app initialized successfully and ready to run")
