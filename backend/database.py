# backend/database.py
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from utils.logger import logger  # ✅ Added logger

# --- Load Environment Variables ---
logger.info("Loading environment variables for MongoDB connection")
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URI or not DB_NAME:
    logger.error("❌ Missing MONGO_URI or DB_NAME in environment variables")
else:
    logger.info(f"✅ Environment variables loaded: DB_NAME={DB_NAME}")

# --- Initialize MongoDB Client ---
try:
    logger.info(f"Attempting to connect to MongoDB at {MONGO_URI}")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    logger.info(f"✅ Successfully connected to MongoDB database: {DB_NAME}")
except Exception as e:
    logger.error(f"❌ Failed to initialize MongoDB client: {e}", exc_info=True)
    raise e

# --- Define Collections ---
try:
    users_collection = db["users"]
    resumes_collection = db["resumes"]
    resume_reviews_collection = db["resume_reviews"]
    applications_collection = db["applications"]
    profiles_collection = db["profiles"]
    jobs_collection = db["jobs"]
    job_user_collection = db["job_user_links"]
    locations_collection = db["locations"]
    saved_jobs_collection = db["saved_jobs"]

    logger.info("✅ MongoDB collections initialized successfully")
except Exception as e:
    logger.error(f"❌ Error initializing collections: {e}", exc_info=True)
    raise e

# --- GridFS Initialization ---
try:
    fs = AsyncIOMotorGridFSBucket(db)
    logger.info("✅ GridFS bucket initialized for resume file storage")
except Exception as e:
    logger.error(f"❌ Failed to initialize GridFS bucket: {e}", exc_info=True)
    raise e
