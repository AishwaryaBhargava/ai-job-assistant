from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import profiles_collection
from services import recommendation_service
from services.ai_service import cosine_similarity
from utils.logger import logger

CACHE_TTL_HOURS = 24


def _collect_profile_skills(profile: Dict[str, Any]) -> List[str]:
    value = profile.get("skills")
    if isinstance(value, list):
        return value
    return []


def _normalize_skill_set(values: List[str]) -> List[str]:
    unique: List[str] = []
    for item in values:
        cleaned = (item or "").strip()
        if cleaned and cleaned.lower() not in [existing.lower() for existing in unique]:
            unique.append(cleaned)
    return unique


def _skill_overlap(profile_skills: List[str], job_skills: List[str]) -> Dict[str, List[str]]:
    logger.info(f"Calculating skill overlap between {len(profile_skills)} profile skills and {len(job_skills)} job skills")
    
    try:
        profile_set = {item.lower(): item for item in profile_skills}
        job_set = {item.lower(): item for item in job_skills}

        matched = [profile_set[key] for key in profile_set.keys() & job_set.keys()]
        gaps = [job_set[key] for key in job_set.keys() - profile_set.keys()]
        
        result = {"matched": sorted(matched), "gaps": sorted(gaps)}
        logger.info(f"✅ Skill overlap calculated: {len(matched)} matched, {len(gaps)} gaps")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to calculate skill overlap: {e}", exc_info=True)
        raise


async def _load_profile(user_id: str) -> Optional[Dict[str, Any]]:
    logger.info(f"Loading profile for user_id={user_id}")
    
    try:
        profile = await profiles_collection.find_one({"user_id": user_id})
        
        if profile:
            logger.info(f"✅ Profile loaded for user_id={user_id}")
        else:
            logger.warning(f"Profile not found for user_id={user_id}")
        
        return profile
    
    except Exception as e:
        logger.error(f"❌ Failed to load profile for user_id={user_id}: {e}", exc_info=True)
        raise


async def compute_resume_fit(user_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    job_id = job.get("_id")
    logger.info(f"Computing resume fit for user_id={user_id}, job_id={job_id}")
    
    try:
        profile = await _load_profile(user_id)
        if not profile:
            logger.warning(f"Profile not found for resume scoring for user_id={user_id}")
            raise ValueError("Profile not found for resume scoring")

        resume_vector = await recommendation_service.get_resume_embedding(profile)
        job_vector = await recommendation_service.get_job_embedding(job)

        similarity = 0.0
        if resume_vector and job_vector:
            similarity = max(0.0, cosine_similarity(resume_vector, job_vector))
            logger.info(f"Calculated similarity score: {similarity:.3f}")
        else:
            logger.warning(f"Missing embeddings for similarity calculation (resume_vector={bool(resume_vector)}, job_vector={bool(job_vector)})")

        profile_skills = _normalize_skill_set(_collect_profile_skills(profile))
        job_skills = _normalize_skill_set(job.get("skills", []))
        overlap = _skill_overlap(profile_skills, job_skills)

        match_ratio = (len(overlap["matched"]) / len(job_skills)) if job_skills else 0.0
        score = int(round(similarity * 60 + match_ratio * 40))

        summary_bits: List[str] = []
        if similarity:
            summary_bits.append(f"Overall similarity {int(similarity * 100)}%")
        if overlap["matched"]:
            summary_bits.append(f"Matched skills: {', '.join(overlap['matched'])}")
        if overlap["gaps"]:
            summary_bits.append(f"Consider highlighting: {', '.join(overlap['gaps'][:5])}")
        if not summary_bits:
            summary_bits.append("No direct overlap detected; tailor your resume to highlight relevant skills.")

        payload = {
            "score": min(100, max(0, score)),
            "summary": " | ".join(summary_bits)[:400],
            "matched": overlap["matched"],
            "gaps": overlap["gaps"],
            "last_calculated": datetime.utcnow(),
        }
        
        logger.info(f"✅ Resume fit computed successfully for user_id={user_id}, job_id={job_id}: score={payload['score']}")
        return payload
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to compute resume fit for user_id={user_id}, job_id={job_id}: {e}", exc_info=True)
        raise


async def get_or_create_resume_fit(user_id: str, job_id: str) -> Dict[str, Any]:
    logger.info(f"Getting or creating resume fit for user_id={user_id}, job_id={job_id}")
    
    try:
        cached = await recommendation_service.get_cached_resume_score(user_id, job_id)
        
        if cached:
            timestamp = cached.get("updated_at") or cached.get("last_calculated")
            if isinstance(timestamp, datetime):
                age = datetime.utcnow() - timestamp
                if age < timedelta(hours=CACHE_TTL_HOURS):
                    logger.info(f"Using cached resume fit for user_id={user_id}, job_id={job_id} (age: {age})")
                    return cached
                else:
                    logger.info(f"Cached resume fit expired for user_id={user_id}, job_id={job_id} (age: {age})")

        job = await recommendation_service.get_job_detail(job_id)
        if not job:
            logger.warning(f"Job not found for job_id={job_id}")
            raise ValueError("Job not found")

        payload = await compute_resume_fit(user_id, job)
        await recommendation_service.cache_resume_score(user_id, job_id, payload)
        
        logger.info(f"✅ Resume fit created and cached for user_id={user_id}, job_id={job_id}")
        return payload
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get or create resume fit for user_id={user_id}, job_id={job_id}: {e}", exc_info=True)
        raise