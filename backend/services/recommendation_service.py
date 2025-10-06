import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from database import jobs_collection, job_user_collection, profiles_collection
from models.preferences import GuestRecommendationRequest, PreferencePayload
from services.ai_service import cosine_similarity, embed_for_matching
from utils.logger import logger

DEFAULT_LIMIT = 20
MAX_CANDIDATES = 150
SIMILARITY_WEIGHT = 70.0
PREFERENCE_BONUS = 10.0


def _normalize_strings(values: Optional[List[str]]) -> List[str]:
    unique: List[str] = []
    for item in values or []:
        cleaned = (item or "").strip()
        if cleaned and cleaned.lower() not in [existing.lower() for existing in unique]:
            unique.append(cleaned)
    return unique


def _profile_to_text(profile: Dict[str, Any]) -> str:
    logger.info("Converting profile to text representation")
    
    try:
        chunks: List[str] = []
        summary = profile.get("summary") or profile.get("about")
        if isinstance(summary, str):
            chunks.append(summary)

        skills = profile.get("skills") or []
        if skills:
            chunks.append("Skills: " + ", ".join(skills))

        for item in profile.get("work_experience", []) or []:
            if not isinstance(item, dict):
                continue
            role = item.get("role") or item.get("title") or ""
            company = item.get("company") or ""
            tasks = item.get("tasks") or item.get("achievements") or ""
            text = " ".join(part for part in [role, company, tasks] if part)
            if text:
                chunks.append(text)

        for item in profile.get("education", []) or []:
            if not isinstance(item, dict):
                continue
            degree = item.get("degree") or item.get("program") or ""
            school = item.get("school") or item.get("institution") or ""
            year = item.get("year") or item.get("graduation_year") or ""
            text = " ".join(part for part in [degree, school, year] if part)
            if text:
                chunks.append(text)

        result = " \n".join(chunks)
        logger.info(f"✅ Profile converted to text ({len(result)} chars)")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to convert profile to text: {e}", exc_info=True)
        raise


def _job_to_text(job: Dict[str, Any]) -> str:
    logger.info(f"Converting job to text representation for job_id={job.get('_id')}")
    
    try:
        chunks: List[str] = [job.get("title", ""), job.get("company", "")]
        description = job.get("description") or job.get("summary") or ""
        if description:
            chunks.append(description)

        if job.get("skills"):
            chunks.append("Skills: " + ", ".join(job.get("skills", [])))
        if job.get("categories"):
            chunks.append("Categories: " + ", ".join(job.get("categories", [])))
        if job.get("levels"):
            chunks.append("Levels: " + ", ".join(job.get("levels", [])))

        result = " \n".join(filter(None, chunks))
        logger.info(f"✅ Job converted to text ({len(result)} chars)")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to convert job to text: {e}", exc_info=True)
        raise


async def _embed_text(text: str) -> Optional[List[float]]:
    logger.info("Embedding text")
    
    try:
        snippet = (text or "").strip()
        if not snippet:
            logger.info("Text is empty, returning None")
            return None
        
        vectors = await asyncio.to_thread(embed_for_matching, [snippet])
        result = vectors[0] if vectors else None
        logger.info(f"✅ Text embedded successfully")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to embed text: {e}", exc_info=True)
        raise


async def _ensure_resume_embedding(profile: Dict[str, Any]) -> Optional[List[float]]:
    user_id = profile.get("user_id")
    logger.info(f"Ensuring resume embedding for user_id={user_id}")
    
    try:
        cached = profile.get("resume_embedding")
        if isinstance(cached, list) and cached:
            logger.info(f"Using cached resume embedding for user_id={user_id}")
            return cached

        logger.info(f"Generating new resume embedding for user_id={user_id}")
        resume_text = _profile_to_text(profile)
        vector = await _embed_text(resume_text)
        
        if vector:
            await profiles_collection.update_one(
                {"user_id": user_id},
                {"$set": {"resume_embedding": vector, "resume_embedding_updated_at": datetime.utcnow()}},
                upsert=True,
            )
            logger.info(f"✅ Resume embedding cached for user_id={user_id}")
        else:
            logger.warning(f"No embedding generated for user_id={user_id}")
        
        return vector
    
    except Exception as e:
        logger.error(f"❌ Failed to ensure resume embedding for user_id={user_id}: {e}", exc_info=True)
        raise


async def _ensure_job_embedding(job: Dict[str, Any]) -> Optional[List[float]]:
    job_id = job.get("_id")
    logger.info(f"Ensuring job embedding for job_id={job_id}")
    
    try:
        cached = job.get("embedding")
        if isinstance(cached, list) and cached:
            logger.info(f"Using cached job embedding for job_id={job_id}")
            return cached

        logger.info(f"Generating new job embedding for job_id={job_id}")
        text = _job_to_text(job)
        vector = await _embed_text(text)
        
        if vector:
            await jobs_collection.update_one(
                {"_id": job_id},
                {"$set": {"embedding": vector, "embedding_updated_at": datetime.utcnow()}},
            )
            logger.info(f"✅ Job embedding cached for job_id={job_id}")
        else:
            logger.warning(f"No embedding generated for job_id={job_id}")
        
        return vector
    
    except Exception as e:
        logger.error(f"❌ Failed to ensure job embedding for job_id={job_id}: {e}", exc_info=True)
        raise


def _base_job_query(preferences: PreferencePayload) -> Dict[str, Any]:
    logger.info("Building base job query from preferences")
    
    try:
        query: Dict[str, Any] = {"status": {"$ne": "closed"}}

        locations = _normalize_strings(preferences.locations)
        if locations:
            clauses: List[Dict[str, Any]] = [{"locations": {"$in": locations}}]
            if preferences.remote_ok:
                clauses.append({"work_modes": {"$in": ["remote", "hybrid"]}})
            query["$or"] = clauses
        elif preferences.remote_ok:
            query["work_modes"] = {"$in": ["remote", "hybrid"]}

        if preferences.role_families:
            query["categories"] = {"$in": preferences.role_families}
        if preferences.seniority_levels:
            query["levels"] = {"$in": preferences.seniority_levels}
        if preferences.industries_like:
            query["metadata.industry"] = {"$in": preferences.industries_like}
        if preferences.company_sizes:
            query["metadata.company_size"] = {"$in": preferences.company_sizes}

        logger.info(f"✅ Base job query built with {len(query)} conditions")
        return query
    
    except Exception as e:
        logger.error(f"❌ Failed to build base job query: {e}", exc_info=True)
        raise


async def _load_jobs(preferences: PreferencePayload) -> List[Dict[str, Any]]:
    logger.info(f"Loading jobs with max candidates={MAX_CANDIDATES}")
    
    try:
        query = _base_job_query(preferences)
        cursor = jobs_collection.find(query).sort("last_seen_active", -1).limit(MAX_CANDIDATES)
        jobs = await cursor.to_list(length=MAX_CANDIDATES)
        logger.info(f"✅ Loaded {len(jobs)} jobs")
        return jobs
    
    except Exception as e:
        logger.error(f"❌ Failed to load jobs: {e}", exc_info=True)
        raise


def _extract_profile_skills(profile: Dict[str, Any]) -> List[str]:
    skills = profile.get("skills") or []
    if isinstance(skills, list):
        return skills
    return []


def _evaluate_preferences(job: Dict[str, Any], preferences: PreferencePayload, profile_skills: List[str]) -> Tuple[float, List[str]]:
    logger.info(f"Evaluating preferences for job_id={job.get('_id')}")
    
    try:
        score = 0.0
        reasons: List[str] = []

        categories = set(item.lower() for item in job.get("categories", []))
        if preferences.role_families:
            overlap = categories.intersection(item.lower() for item in preferences.role_families)
            if overlap:
                score += PREFERENCE_BONUS
                reasons.append("Matches preferred role focus")

        levels = set(item.lower() for item in job.get("levels", []))
        if preferences.seniority_levels:
            overlap = levels.intersection(item.lower() for item in preferences.seniority_levels)
            if overlap:
                score += PREFERENCE_BONUS
                reasons.append("Requested seniority level")

        industries = set()
        if isinstance(job.get("metadata"), dict):
            industries = set(item.lower() for item in job["metadata"].get("industry", []))
            company_size = str(job["metadata"].get("company_size", "")).lower()
            if preferences.company_sizes and company_size:
                if any(company_size == item.lower() for item in preferences.company_sizes):
                    score += PREFERENCE_BONUS
                    reasons.append("Preferred company size")

        if preferences.industries_like:
            overlap = industries.intersection(item.lower() for item in preferences.industries_like)
            if overlap:
                score += PREFERENCE_BONUS
                reasons.append("Preferred industry")
        if preferences.industries_avoid:
            avoid = industries.intersection(item.lower() for item in preferences.industries_avoid)
            if avoid:
                score -= PREFERENCE_BONUS
                reasons.append("Industry on avoid list")

        job_skills = set(item.lower() for item in job.get("skills", []))
        profile_skill_set = set(item.lower() for item in profile_skills)
        if job_skills and profile_skill_set:
            overlap = job_skills.intersection(profile_skill_set)
            if overlap:
                score += PREFERENCE_BONUS
                reasons.append(f"Skill overlap: {', '.join(sorted(list(overlap)))[:60]}")

        logger.info(f"✅ Preferences evaluated: score={score}, reasons={len(reasons)}")
        return score, reasons
    
    except Exception as e:
        logger.error(f"❌ Failed to evaluate preferences for job_id={job.get('_id')}: {e}", exc_info=True)
        raise


async def _rank_jobs(
    jobs: List[Dict[str, Any]],
    preferences: PreferencePayload,
    profile: Dict[str, Any],
    resume_vector: Optional[List[float]],
) -> List[Dict[str, Any]]:
    logger.info(f"Ranking {len(jobs)} jobs")
    
    try:
        ranked: List[Dict[str, Any]] = []
        profile_skills = _extract_profile_skills(profile)

        for job in jobs:
            reasons: List[str] = []
            pref_score, pref_reasons = _evaluate_preferences(job, preferences, profile_skills)
            reasons.extend(pref_reasons)

            sim_score = 0.0
            if resume_vector:
                job_vector = await _ensure_job_embedding(job)
                if job_vector:
                    similarity = cosine_similarity(resume_vector, job_vector)
                    if similarity > 0:
                        sim_score = similarity * SIMILARITY_WEIGHT
                        reasons.append(f"Resume alignment {int(similarity * 100)}%")

            total_score = min(100.0, max(0.0, sim_score + pref_score))
            ranked.append(
                {
                    "job": job,
                    "score": round(total_score, 2),
                    "reasons": reasons,
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        logger.info(f"✅ Jobs ranked successfully, top score={ranked[0]['score'] if ranked else 0}")
        return ranked
    
    except Exception as e:
        logger.error(f"❌ Failed to rank jobs: {e}", exc_info=True)
        raise


async def _fetch_user_states(user_id: str) -> Dict[str, Dict[str, Any]]:
    logger.info(f"Fetching user states for user_id={user_id}")
    
    try:
        cursor = job_user_collection.find({"user_id": user_id})
        records = await cursor.to_list(length=None)
        mapping: Dict[str, Dict[str, Any]] = {}
        for record in records:
            job_id = record.get("job_id")
            if not job_id:
                continue
            mapping[job_id] = {
                "state": record.get("state"),
                "resume_score_cache": record.get("resume_score_cache"),
            }
        logger.info(f"✅ Fetched {len(mapping)} user states for user_id={user_id}")
        return mapping
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch user states for user_id={user_id}: {e}", exc_info=True)
        raise


def _serialize_job_result(entry: Dict[str, Any], user_states: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    job = entry["job"]
    job_id = str(job["_id"])
    metadata = job.get("metadata", {}) if isinstance(job.get("metadata"), dict) else {}

    response = {
        "id": job_id,
        "title": job.get("title"),
        "company": job.get("company"),
        "locations": job.get("locations", []),
        "work_modes": job.get("work_modes", []),
        "categories": job.get("categories", []),
        "levels": job.get("levels", []),
        "skills": job.get("skills", []),
        "description": job.get("description"),
        "salary": job.get("salary"),
        "url": job.get("url"),
        "status": job.get("status", "active"),
        "source": job.get("source"),
        "match_score": entry["score"],
        "matched_reasons": entry["reasons"],
        "metadata": metadata,
    }

    state = user_states.get(job_id)
    if state:
        response["user_state"] = state.get("state")
        if state.get("resume_score_cache"):
            response["resume_score_cache"] = state["resume_score_cache"]

    return response


async def recommend_for_user(user_id: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    logger.info(f"Generating recommendations for user_id={user_id}, limit={limit}")
    
    try:
        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile:
            logger.warning(f"Profile not found for user_id={user_id}")
            return []

        preferences_data = profile.get("preferences")
        if not preferences_data:
            logger.warning(f"No preferences found for user_id={user_id}")
            return []

        payload = {key: preferences_data.get(key) for key in PreferencePayload.__fields__.keys()}
        preferences = PreferencePayload.parse_obj(payload)

        resume_vector = await _ensure_resume_embedding(profile)
        jobs = await _load_jobs(preferences)
        
        if not jobs:
            logger.info(f"No jobs found matching preferences for user_id={user_id}")
            return []

        ranked = await _rank_jobs(jobs, preferences, profile, resume_vector)
        user_states = await _fetch_user_states(user_id)
        results = [_serialize_job_result(entry, user_states) for entry in ranked[:limit]]
        
        logger.info(f"✅ Generated {len(results)} recommendations for user_id={user_id}")
        return results
    
    except Exception as e:
        logger.error(f"❌ Failed to generate recommendations for user_id={user_id}: {e}", exc_info=True)
        raise


async def recommend_for_guest(request: GuestRecommendationRequest) -> List[Dict[str, Any]]:
    logger.info(f"Generating guest recommendations with limit={request.limit}")
    
    try:
        preferences = request.preferences
        profile_stub = {
            "skills": preferences.skills,
            "work_experience": [],
            "education": [],
        }
        resume_vector: Optional[List[float]] = None
        
        if request.resume_snippets:
            logger.info(f"Embedding {len(request.resume_snippets)} resume snippets for guest")
            resume_vector = await _embed_text(" \n".join(request.resume_snippets))

        jobs = await _load_jobs(preferences)
        
        if not jobs:
            logger.info("No jobs found matching guest preferences")
            return []

        ranked = await _rank_jobs(jobs, preferences, profile_stub, resume_vector)
        results = [_serialize_job_result(entry, {}) for entry in ranked[: request.limit]]
        
        logger.info(f"✅ Generated {len(results)} guest recommendations")
        return results
    
    except Exception as e:
        logger.error(f"❌ Failed to generate guest recommendations: {e}", exc_info=True)
        raise


async def get_job_detail(job_id: str) -> Optional[Dict[str, Any]]:
    logger.info(f"Fetching job detail for job_id={job_id}")
    
    try:
        try:
            oid = ObjectId(job_id)
        except Exception:
            logger.warning(f"Invalid ObjectId format for job_id={job_id}")
            return None
        
        job = await jobs_collection.find_one({"_id": oid})
        
        if job:
            logger.info(f"✅ Job detail retrieved for job_id={job_id}")
        else:
            logger.warning(f"Job not found for job_id={job_id}")
        
        return job
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch job detail for job_id={job_id}: {e}", exc_info=True)
        raise


async def upsert_job(job_payload: Dict[str, Any]) -> str:
    source = job_payload.get("source")
    source_id = job_payload.get("source_id")
    logger.info(f"Upserting job from source={source}, source_id={source_id}")
    
    try:
        now = datetime.utcnow()
        job_payload.setdefault("status", "active")
        job_payload.setdefault("last_seen_active", now)
        
        query = {"source": source, "source_id": source_id}
        existing = await jobs_collection.find_one(query, {"_id": 1})
        
        if existing:
            await jobs_collection.update_one(
                {"_id": existing["_id"]}, 
                {"$set": job_payload, "$setOnInsert": {"created_at": now}}
            )
            job_id = str(existing["_id"])
            logger.info(f"✅ Job updated for source={source}, source_id={source_id}, job_id={job_id}")
            return job_id
        
        result = await jobs_collection.insert_one({**job_payload, "created_at": now})
        job_id = str(result.inserted_id)
        logger.info(f"✅ Job inserted for source={source}, source_id={source_id}, job_id={job_id}")
        return job_id
    
    except Exception as e:
        logger.error(f"❌ Failed to upsert job for source={source}, source_id={source_id}: {e}", exc_info=True)
        raise


async def mark_job_status(job_id: str, status: str) -> None:
    logger.info(f"Marking job status for job_id={job_id}, status={status}")
    
    try:
        try:
            oid = ObjectId(job_id)
        except Exception:
            logger.warning(f"Invalid ObjectId format for job_id={job_id}")
            return
        
        await jobs_collection.update_one(
            {"_id": oid}, 
            {"$set": {"status": status, "last_status_change": datetime.utcnow()}}
        )
        logger.info(f"✅ Job status marked for job_id={job_id}, status={status}")
    
    except Exception as e:
        logger.error(f"❌ Failed to mark job status for job_id={job_id}: {e}", exc_info=True)
        raise


async def save_job_for_user(user_id: str, job_id: str, state: str) -> None:
    logger.info(f"Saving job for user_id={user_id}, job_id={job_id}, state={state}")
    
    try:
        now = datetime.utcnow()
        await job_user_collection.update_one(
            {"user_id": user_id, "job_id": job_id},
            {
                "$set": {"state": state, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        logger.info(f"✅ Job saved for user_id={user_id}, job_id={job_id}, state={state}")
    
    except Exception as e:
        logger.error(f"❌ Failed to save job for user_id={user_id}, job_id={job_id}: {e}", exc_info=True)
        raise


async def delete_saved_job(user_id: str, job_id: str) -> None:
    logger.info(f"Deleting saved job for user_id={user_id}, job_id={job_id}")
    
    try:
        await job_user_collection.delete_one({"user_id": user_id, "job_id": job_id})
        logger.info(f"✅ Saved job deleted for user_id={user_id}, job_id={job_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to delete saved job for user_id={user_id}, job_id={job_id}: {e}", exc_info=True)
        raise


async def list_user_jobs(user_id: str) -> List[Dict[str, Any]]:
    logger.info(f"Listing jobs for user_id={user_id}")
    
    try:
        cursor = job_user_collection.find({"user_id": user_id})
        links = await cursor.to_list(length=None)
        
        if not links:
            logger.info(f"No saved jobs found for user_id={user_id}")
            return []
        
        job_ids = [link.get("job_id") for link in links if link.get("job_id")]
        oid_map: Dict[str, ObjectId] = {}
        for job_id in job_ids:
            try:
                oid_map[job_id] = ObjectId(job_id)
            except Exception:
                logger.warning(f"Invalid job_id format: {job_id}")
                continue
        
        if not oid_map:
            logger.warning(f"No valid job IDs found for user_id={user_id}")
            return []
        
        jobs = await jobs_collection.find({"_id": {"$in": list(oid_map.values())}}).to_list(length=None)
        state_map = {
            link.get("job_id"): {
                "state": link.get("state"),
                "resume_score_cache": link.get("resume_score_cache"),
            }
            for link in links
            if link.get("job_id")
        }
        
        results: List[Dict[str, Any]] = []
        for job in jobs:
            entry = {
                "job": job,
                "score": 0.0,
                "reasons": [],
            }
            serialized = _serialize_job_result(entry, state_map)
            results.append(serialized)
        
        logger.info(f"✅ Listed {len(results)} jobs for user_id={user_id}")
        return results
    
    except Exception as e:
        logger.error(f"❌ Failed to list jobs for user_id={user_id}: {e}", exc_info=True)
        raise

async def cache_resume_score(user_id: str, job_id: str, payload: Dict[str, Any]) -> None:
    logger.info(f"Caching resume score for user_id={user_id}, job_id={job_id}")
    
    try:
        stored = dict(payload)
        stored["updated_at"] = datetime.utcnow()
        await job_user_collection.update_one(
            {"user_id": user_id, "job_id": job_id},
            {"$set": {"resume_score_cache": stored}},
            upsert=True,
        )
        logger.info(f"✅ Resume score cached for user_id={user_id}, job_id={job_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to cache resume score for user_id={user_id}, job_id={job_id}: {e}", exc_info=True)
        raise