import asyncio
import json
import math
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from models.review import ResumeReviewResult
from utils.logger import logger

load_dotenv()

API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CHAT_MODEL = os.getenv("AZURE_AI_DEPLOYMENT") or "DeepSeek-R1"
EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

if not API_KEY or not ENDPOINT:
    raise ValueError("Missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT in environment variables.")

if not EMBEDDING_MODEL:
    raise ValueError("Missing AZURE_OPENAI_EMBEDDING_DEPLOYMENT in environment variables.")

client = OpenAI(
    api_key=API_KEY,
    base_url=f"{ENDPOINT}/openai/v1"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json_block(text: str) -> str:
    logger.info("Extracting JSON block from AI response")
    
    try:
        snippet = (text or "").strip()
        if not snippet:
            logger.warning("AI response was empty")
            raise ValueError("AI response was empty.")
        
        decoder = json.JSONDecoder()
        for start_char in ("{", "["):
            start = snippet.find(start_char)
            while start != -1:
                try:
                    _, end = decoder.raw_decode(snippet[start:])
                    logger.info("✅ JSON block extracted successfully")
                    return snippet[start:start + end]
                except json.JSONDecodeError:
                    start = snippet.find(start_char, start + 1)
        
        logger.warning(f"AI did not return valid JSON")
        raise ValueError(f"AI did not return valid JSON: {text}")
    
    except Exception as e:
        logger.error(f"❌ Failed to extract JSON block: {e}", exc_info=True)
        raise


def _load_json(text: str) -> Dict[str, Any]:
    logger.info("Loading JSON from extracted text")
    
    try:
        payload = _extract_json_block(text)
        result = json.loads(payload)
        logger.info("✅ JSON loaded successfully")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to load JSON: {e}", exc_info=True)
        raise


def _clean_similarity(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 3)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _batched_embeddings(texts: List[str]) -> List[List[float]]:
    logger.info(f"Generating embeddings for {len(texts)} text(s)")
    
    try:
        if not texts:
            logger.info("No texts provided for embedding")
            return []
        
        if not EMBEDDING_MODEL:
            logger.warning("AZURE_OPENAI_EMBEDDING_DEPLOYMENT not configured")
            raise ValueError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT must be configured for resume scoring.")
        
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        logger.info(f"✅ Embeddings generated successfully for {len(texts)} text(s)")
        return [item.embedding for item in response.data]
    
    except Exception as e:
        logger.error(f"❌ Failed to generate embeddings: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# LLM powered parsing utilities
# ---------------------------------------------------------------------------

def generate_answers_with_ai(profile_text: str, job_description: str) -> str:
    """Generate a tailored answer for "Why are you a good fit?"."""
    logger.info("Generating AI answer for 'Why are you a good fit?'")
    
    try:
        prompt = f"""
    You are an AI assistant helping with job applications.

    Candidate profile:
    {profile_text}

    Job description:
    {job_description}

    Write a professional, confident answer (150-200 words) to the question:
    "Why are you a good fit for this role?"

    Requirements:
    - Return only the final answer in plain text (no bullet points, no JSON).
    - Do not include hidden reasoning or <think> blocks.
    """.strip()

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Always reply in plain text only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.7,
        )

        answer_text = getattr(response.choices[0].message, "content", "") or ""
        cleaned_answer = re.sub(r"<think>.*?</think>", "", answer_text, flags=re.S).strip()
        logger.info("✅ AI answer generated successfully")
        return cleaned_answer
    
    except Exception as e:
        logger.error(f"❌ Failed to generate AI answer: {e}", exc_info=True)
        raise


def parse_resume_with_ai(resume_text: str) -> Dict[str, Any]:
    """Parse a resume into a predictable structured JSON format."""
    logger.info("Parsing resume with AI")
    
    try:
        prompt = f"""
    Extract structured data from the resume text and return strict JSON matching this schema:
    {{
      "name": "string",
      "email": "string",
      "phone": "string",
      "linkedin": "string",
      "github": "string",
      "twitter": "string",
      "portfolio": "string",
      "location": "string",
      "websites": ["string"],
      "skills": ["string"],
      "education": [
        {{
          "degree": "string",
          "school": "string",
          "year": "string",
          "gpa": "string"
        }}
      ],
      "work_experience": [
        {{
          "company": "string",
          "role": "string",
          "duration": "string",
          "location": "string",
          "tasks": "string"
        }}
      ]
    }}

    Rules:
    - Use empty strings ("") or empty lists when information is missing.
    - Skills must be a deduplicated list of short skill phrases.
    - Tasks must be a single sentence (no bullet characters).
    - Return only JSON.

    Resume:
    {resume_text}
    """.strip()

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You output only strict, valid JSON for the requested schema."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        raw = (response.choices[0].message.content or "").strip()
        data = _load_json(raw)

        result: Dict[str, Any] = {
            "name": str(data.get("name", "") or ""),
            "email": str(data.get("email", "") or ""),
            "phone": str(data.get("phone", "") or ""),
            "linkedin": str(data.get("linkedin", "") or ""),
            "github": str(data.get("github", "") or ""),
            "twitter": str(data.get("twitter", "") or ""),
            "portfolio": str(data.get("portfolio", "") or ""),
            "location": str(data.get("location", "") or ""),
            "websites": data.get("websites", []) if isinstance(data.get("websites"), list) else [],
            "skills": [],
            "education": [],
            "work_experience": [],
        }

        # Skills cleanup
        skills_raw = data.get("skills", [])
        if isinstance(skills_raw, str):
            parts = re.split(r"[,\n;|]+", skills_raw)
            skills_raw = [p.strip() for p in parts if p.strip()]
        if isinstance(skills_raw, list):
            seen = set()
            for s in skills_raw:
                label = str(s).strip()
                if label and label.lower() not in seen:
                    seen.add(label.lower())
                    result["skills"].append(label)

        # Education cleanup
        education_raw = data.get("education") or []
        if isinstance(education_raw, dict):
            education_raw = [education_raw]
        if isinstance(education_raw, list):
            for item in education_raw:
                entry = {
                    "degree": str((item or {}).get("degree", "") or ""),
                    "school": str((item or {}).get("school", "") or ""),
                    "year": str((item or {}).get("year", "") or ""),
                    "gpa": str((item or {}).get("gpa", "") or ""),
                }
                result["education"].append(entry)

        # Work experience cleanup
        experience_raw = data.get("work_experience") or []
        if isinstance(experience_raw, dict):
            experience_raw = [experience_raw]
        if isinstance(experience_raw, list):
            for item in experience_raw:
                tasks_value = (item or {}).get("tasks", "")
                if isinstance(tasks_value, list):
                    sentence = ". ".join(
                        [str(t).strip().rstrip(".") for t in tasks_value if str(t).strip()]
                    ).strip()
                    if sentence:
                        tasks_value = sentence + "."
                    else:
                        tasks_value = ""
                else:
                    tasks_value = re.sub(r"\s+", " ", str(tasks_value)).strip()
                entry = {
                    "company": str((item or {}).get("company", "") or ""),
                    "role": str((item or {}).get("role", "") or ""),
                    "duration": str((item or {}).get("duration", "") or ""),
                    "location": str((item or {}).get("location", "") or ""),
                    "tasks": tasks_value,
                }
                result["work_experience"].append(entry)

        logger.info(f"✅ Resume parsed successfully with {len(result['skills'])} skills, {len(result['education'])} education entries, {len(result['work_experience'])} work experiences")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to parse resume: {e}", exc_info=True)
        raise


def parse_job_description_with_ai(job_description: str) -> Dict[str, Any]:
    """Extract key requirements from a job description."""
    logger.info("Parsing job description with AI")
    
    try:
        prompt = f"""
    Analyze the job description and return structured JSON with the key requirements.

    Schema:
    {{
      "skills": [
        {{"name": "string", "critical": true, "notes": "string"}}
      ],
      "experience": [
        {{"description": "string", "critical": true}}
      ],
      "education": [
        {{"name": "string", "critical": true}}
      ],
      "keywords": [
        {{"term": "string", "critical": true}}
      ]
    }}

    Notes:
    - Mark an item as critical when the description states it is required, must-have, or essential.
    - Use concise phrasing for each item.
    - Use empty lists when a category is not mentioned.
    - Return strictly valid JSON.

    Job description:
    {job_description}
    """.strip()

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You output only strict, valid JSON for the requested schema."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        raw = (response.choices[0].message.content or "").strip()
        data = _load_json(raw)

        def _normalize_list(value: Any) -> List[Dict[str, Any]]:
            if isinstance(value, list):
                return [dict(item or {}) for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return [dict(value)]
            return []

        result = {
            "skills": _normalize_list(data.get("skills")),
            "experience": _normalize_list(data.get("experience")),
            "education": _normalize_list(data.get("education")),
            "keywords": _normalize_list(data.get("keywords")),
        }
        
        logger.info(f"✅ Job description parsed successfully with {len(result['skills'])} skills, {len(result['experience'])} experience requirements, {len(result['education'])} education requirements, {len(result['keywords'])} keywords")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to parse job description: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Scoring utilities
# ---------------------------------------------------------------------------

DimensionResult = Dict[str, Any]


def _score_requirements(
    requirements: List[Dict[str, Any]],
    evidence_texts: List[str],
    *,
    label_field: str,
    threshold: float = 0.72,
) -> DimensionResult:
    logger.info(f"Scoring requirements with label_field={label_field}, threshold={threshold}")
    
    try:
        cleaned_requirements = []
        for item in requirements:
            label = str(item.get(label_field, "") or "").strip()
            if not label:
                continue
            cleaned_requirements.append({
                "label": label,
                "critical": bool(item.get("critical", False)),
                "notes": str(item.get("notes", "") or ""),
            })

        if not cleaned_requirements:
            logger.info("No requirements to score, returning 100% score")
            return {
                "score": 100,
                "applicable": False,
                "matched": [],
                "missing": [],
                "weight": 0.0,
            }

        evidence = [text.strip() for text in evidence_texts if str(text).strip()]
        if not evidence:
            logger.warning("No evidence provided for scoring")
            missing_payload = [
                {
                    "requirement": item["label"],
                    "critical": item["critical"],
                    "similarity": None,
                }
                for item in cleaned_requirements
            ]
            total_weight = sum(2 if item["critical"] else 1 for item in cleaned_requirements)
            return {
                "score": 0,
                "applicable": True,
                "matched": [],
                "missing": missing_payload,
                "weight": float(total_weight),
            }

        combined_texts = [item["label"] for item in cleaned_requirements] + evidence
        embeddings = _batched_embeddings(combined_texts)
        req_count = len(cleaned_requirements)
        requirement_embeddings = embeddings[:req_count]
        evidence_embeddings = embeddings[req_count:]

        matched: List[Dict[str, Any]] = []
        missing: List[Dict[str, Any]] = []

        for idx, item in enumerate(cleaned_requirements):
            req_vector = requirement_embeddings[idx]
            best_match: Optional[Dict[str, Any]] = None
            best_similarity = -1.0

            for evidence_idx, ev_vector in enumerate(evidence_embeddings):
                similarity = _cosine_similarity(req_vector, ev_vector)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        "requirement": item["label"],
                        "critical": item["critical"],
                        "matched_text": evidence[evidence_idx],
                        "similarity": _clean_similarity(similarity),
                    }

            if best_match and best_similarity >= threshold:
                matched.append(best_match)
            else:
                missing.append(
                    {
                        "requirement": item["label"],
                        "critical": item["critical"],
                        "similarity": _clean_similarity(best_similarity if best_similarity > -1 else None),
                    }
                )

        total_weight = sum(2 if item.get("critical") else 1 for item in cleaned_requirements)
        matched_weight = sum(2 if item.get("critical") else 1 for item in matched)
        score = int(round(100 * matched_weight / total_weight)) if total_weight else 0

        logger.info(f"✅ Requirements scored successfully: {score}% ({len(matched)} matched, {len(missing)} missing)")
        
        return {
            "score": score,
            "applicable": True,
            "matched": matched,
            "missing": missing,
            "weight": float(total_weight),
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to score requirements: {e}", exc_info=True)
        raise


def _score_keywords(requirements: List[Dict[str, Any]], resume_text: str, extra_evidence: List[str]) -> DimensionResult:
    logger.info("Scoring keywords")
    texts = [resume_text] + extra_evidence
    return _score_requirements(requirements, texts, label_field="term")


def _compose_experience_evidence(resume_data: Dict[str, Any]) -> List[str]:
    evidence: List[str] = []
    for item in resume_data.get("work_experience", []):
        parts = [item.get("role", ""), item.get("company", ""), item.get("tasks", "")]
        text = " ".join(part for part in parts if part).strip()
        if text:
            evidence.append(text)
    return evidence


def _compose_education_evidence(resume_data: Dict[str, Any]) -> List[str]:
    evidence: List[str] = []
    for item in resume_data.get("education", []):
        parts = [item.get("degree", ""), item.get("school", ""), item.get("year", ""), item.get("gpa", "")]
        text = " ".join(part for part in parts if part).strip()
        if text:
            evidence.append(text)
    return evidence


DIMENSION_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.35,
    "education": 0.15,
    "keywords": 0.15,
}


def score_resume_against_job(
    resume_data: Dict[str, Any],
    job_data: Dict[str, Any],
    *,
    resume_text: str,
) -> Dict[str, Any]:
    logger.info("Scoring resume against job description")
    
    try:
        skills_result = _score_requirements(job_data.get("skills", []), resume_data.get("skills", []), label_field="name")
        experience_result = _score_requirements(
            job_data.get("experience", []),
            _compose_experience_evidence(resume_data),
            label_field="description",
        )
        education_result = _score_requirements(
            job_data.get("education", []),
            _compose_education_evidence(resume_data),
            label_field="name",
        )
        keywords_result = _score_keywords(
            job_data.get("keywords", []),
            resume_text,
            resume_data.get("skills", []) + _compose_experience_evidence(resume_data),
        )

        breakdown = {
            "skills": skills_result,
            "experience": experience_result,
            "education": education_result,
            "keywords": keywords_result,
        }

        active_weight = 0.0
        weighted_score = 0.0
        for key, result in breakdown.items():
            if result.get("applicable"):
                weight = DIMENSION_WEIGHTS.get(key, 0.0)
                active_weight += weight
                weighted_score += weight * result["score"]

        overall_score = int(round(weighted_score / active_weight)) if active_weight else 0

        for value in breakdown.values():
            for entry in value.get("matched", []):
                entry["similarity"] = _clean_similarity(entry.get("similarity"))
            for entry in value.get("missing", []):
                entry["similarity"] = _clean_similarity(entry.get("similarity"))

        logger.info(f"✅ Resume scored successfully with overall score: {overall_score}%")
        
        return {
            "overall_score": overall_score,
            "breakdown": breakdown,
            "weights": DIMENSION_WEIGHTS,
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to score resume against job: {e}", exc_info=True)
        raise


def _summarize_missing_items(breakdown: Dict[str, Any]) -> Dict[str, List[str]]:
    summary: Dict[str, List[str]] = {}
    for key, value in breakdown.items():
        missing_items = value.get("missing", [])
        if missing_items:
            summary[key] = [item.get("requirement", "") for item in missing_items if item.get("requirement")]
    return summary


def _generate_suggestions(
    resume_text: str,
    job_description: str,
    missing_summary: Dict[str, List[str]],
) -> List[str]:
    logger.info("Generating improvement suggestions")
    
    try:
        suggestions: List[str] = []

        def _summarize(items: List[str], max_items: int = 5) -> str:
            seen: List[str] = []
            for entry in items:
                cleaned = entry.strip()
                if cleaned and cleaned not in seen:
                    seen.append(cleaned)
                if len(seen) >= max_items:
                    break
            return ', '.join(seen)

        if missing_summary.get('skills'):
            skill_list = _summarize(missing_summary['skills'])
            suggestions.append(
                f"Highlight or add specific accomplishments that demonstrate: {skill_list}."
                if skill_list
                else "Highlight measurable achievements for the required skills."
            )

        if missing_summary.get('experience'):
            experience_list = _summarize(missing_summary['experience'])
            suggestions.append(
                f"Describe projects or roles that cover: {experience_list}."
                if experience_list
                else "Add concise examples of relevant experience."
            )

        if missing_summary.get('education'):
            edu_list = _summarize(missing_summary['education'])
            suggestions.append(
                f"Call out education or certifications related to: {edu_list}."
                if edu_list
                else "List any degrees or certifications that match the role."
            )

        if missing_summary.get('keywords'):
            keyword_list = _summarize(missing_summary['keywords'])
            suggestions.append(
                f"Weave these keywords into your resume summary or bullet points: {keyword_list}."
                if keyword_list
                else "Incorporate the role's terminology so the resume mirrors the job posting."
            )

        if not suggestions:
            suggestions = [
                "Great alignment overall. Tighten your opening summary with one or two quantified wins.",
                "Double-check formatting and ensure the most relevant skills are near the top of the resume.",
            ]

        logger.info(f"✅ Generated {len(suggestions[:3])} suggestions")
        return suggestions[:3]
    
    except Exception as e:
        logger.error(f"❌ Failed to generate suggestions: {e}", exc_info=True)
        raise



# ---------------------------------------------------------------------------
# Resume review utilities
# ---------------------------------------------------------------------------

RESUME_REVIEW_SCHEMA = """{
  "ats_score": integer (0-100),
  "summary_headline": short string <= 140 chars summarising strongest hook,
  "overall_feedback": string with 2-3 sentences covering strengths and risks,
  "weak_sections": [
    {"section": string, "issue": string, "evidence": string quoting or paraphrasing resume}
  ],
  "phrasing_suggestions": [
    {"original": string, "improved": string, "reason": string}
  ],
  "missing_keywords": {
    "role_family": string guess of likely job focus,
    "must_have": array of critical keywords,
    "nice_to_have": array of bonus keywords
  },
  "quick_fixes": [
    {"title": string, "description": string, "impact": one of [High, Medium, Low], "effort_minutes": integer >= 5}
  ]
}"""

RESUME_REVIEW_PROMPT = """You are an applicant tracking system specialist and senior recruiter. Review the resume text and deliver strict JSON matching this schema (no extra keys, no prose):
{schema}
Rules:
- Never add commentary outside the JSON.
- Prefer evidence-driven critiques; cite snippets in "evidence".
- Provide at least two phrasing suggestions when content allows.
- Limit quick_fixes to the top three highest-impact opportunities.
- If data is unavailable, use an empty array rather than null.

Resume text:
<<<
{resume_text}
>>>

Structured summary (for context only):
{resume_summary}
""".strip()

def _truncate_resume_text(text: str, limit: int = 12000) -> str:
    snippet = (text or "").strip()
    if len(snippet) <= limit:
        return snippet
    return snippet[:limit] + "\n...[truncated]..."


def _resume_summary_for_prompt(resume_data: Dict[str, Any]) -> str:
    summary = {
        "skills": (resume_data.get("skills") or [])[:20],
        "top_experience": [
            {
                "title": item.get("title"),
                "company": item.get("company"),
                "achievements": (item.get("achievements") or [])[:2],
            }
            for item in (resume_data.get("work_experience") or [])[:3]
        ],
        "education": [
            {
                "institution": item.get("institution"),
                "degree": item.get("degree"),
                "end_date": item.get("end_date") or item.get("graduation_year"),
            }
            for item in (resume_data.get("education") or [])[:2]
        ],
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


def _compose_resume_review_prompt(resume_text: str, resume_data: Dict[str, Any]) -> str:
    return RESUME_REVIEW_PROMPT.format(
        schema=RESUME_REVIEW_SCHEMA,
        resume_text=_truncate_resume_text(resume_text),
        resume_summary=_resume_summary_for_prompt(resume_data),
    )


def _invoke_resume_review(prompt: str) -> Dict[str, Any]:
    logger.info("Invoking AI for resume review")
    
    try:
        base_messages = [
            {
                "role": "system",
                "content": "You are an ATS analyst. Reply with JSON only; no hidden fields, no markdown.",
            },
            {"role": "user", "content": prompt},
        ]

        reminders = [
            "Return a strict JSON object that matches the provided schema. No prose.",
            "Your previous answer was invalid. Output only the JSON object that matches the schema; start with { and end with }.",
        ]

        last_error: Optional[Exception] = None
        for attempt, reminder in enumerate(reminders, start=1):
            logger.info(f"Resume review attempt {attempt}/{len(reminders)}")
            
            messages = list(base_messages)
            if attempt > 1:
                messages[-1] = {"role": "user", "content": f"{prompt}\n\nREMINDER: {reminder}"}

            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                max_tokens=900,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            answer = getattr(response.choices[0].message, "content", "") or ""
            answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S)
            try:
                payload = _load_json(answer)
                if not isinstance(payload, dict):
                    logger.warning(f"AI did not return a JSON object on attempt {attempt}")
                    raise ValueError(f"AI did not return a JSON object: {payload!r}")

                required_keys = {
                    "ats_score", "overall_feedback", "weak_sections", "phrasing_suggestions", "missing_keywords", "quick_fixes"
                }
                missing_keys = [key for key in required_keys if key not in payload]
                if missing_keys:
                    logger.warning(f"AI payload missing keys on attempt {attempt}: {missing_keys}")
                    snippet = json.dumps(payload, ensure_ascii=False)[:400] if isinstance(payload, dict) else str(payload)
                    raise ValueError(f"AI payload missing keys: {missing_keys} | raw: {snippet}")

                result = ResumeReviewResult.parse_obj(payload)
                logger.info(f"✅ Resume review completed successfully on attempt {attempt}")
                return result.dict()
            except ValueError as exc:
                last_error = exc
                logger.warning(f"Resume review attempt {attempt} failed: {exc}")
                continue

        logger.error("❌ All resume review attempts failed")
        raise ValueError(str(last_error) if last_error else "AI failed to provide a valid review")
    
    except Exception as e:
        logger.error(f"❌ Failed to invoke resume review: {e}", exc_info=True)
        raise

async def review_resume_with_ai(resume_text: str) -> Dict[str, Any]:
    logger.info("Starting resume review with AI")
    
    try:
        if not resume_text or not resume_text.strip():
            logger.warning("Resume text is empty or missing")
            raise ValueError("Resume text is required for review.")

        resume_data = await asyncio.to_thread(parse_resume_with_ai, resume_text)
        prompt = _compose_resume_review_prompt(resume_text, resume_data)
        review = await asyncio.to_thread(_invoke_resume_review, prompt)
        review["resume_snapshot"] = {
            "skills": resume_data.get("skills", []),
            "education": resume_data.get("education", []),
            "work_experience": resume_data.get("work_experience", []),
        }
        review["ats_score"] = int(review.get("ats_score", 0))
        logger.info(f"✅ Resume review completed successfully with ATS score: {review['ats_score']}")
        return review
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to review resume: {e}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Public orchestration API
# ---------------------------------------------------------------------------

async def analyze_resume_with_ai(resume_text: str, job_description: str) -> Dict[str, Any]:
    logger.info("Starting resume analysis with AI")
    
    try:
        resume_task = asyncio.to_thread(parse_resume_with_ai, resume_text)
        job_task = asyncio.to_thread(parse_job_description_with_ai, job_description)
        resume_data, job_data = await asyncio.gather(resume_task, job_task)

        scoring = await asyncio.to_thread(
            score_resume_against_job,
            resume_data,
            job_data,
            resume_text=resume_text,
        )
        missing_summary = _summarize_missing_items(scoring["breakdown"])
        suggestions = _generate_suggestions(resume_text, job_description, missing_summary)

        scoring["suggestions"] = suggestions
        scoring["resume_snapshot"] = {
            "skills": resume_data.get("skills", []),
            "education": resume_data.get("education", []),
            "work_experience": resume_data.get("work_experience", []),
        }
        scoring["job_requirements"] = job_data

        logger.info(f"✅ Resume analysis completed successfully with overall score: {scoring['overall_score']}%")
        return scoring
    
    except Exception as e:
        logger.error(f"❌ Failed to analyze resume: {e}", exc_info=True)
        raise


def embed_for_matching(texts: List[str]) -> List[List[float]]:
    logger.info(f"Embedding {len(texts)} text(s) for matching")
    try:
        result = _batched_embeddings(texts)
        logger.info(f"✅ Embeddings for matching generated successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Failed to embed texts for matching: {e}", exc_info=True)
        raise


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    return _cosine_similarity(vec_a, vec_b)