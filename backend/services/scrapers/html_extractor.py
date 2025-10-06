import json
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from readability import Document
import trafilatura
from utils.logger import logger

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


def extract_job_description(url: str, *, timeout: float = 15.0) -> Optional[str]:
    """Return cleaned job description text for the given posting URL.

    Strategy order:
      1. Parse JSON-LD job posting payloads.
      2. Use readability-lxml to grab the main article body.
      3. Fall back to trafilatura extraction.
      4. Heuristics for common job-description containers.
    """
    logger.info(f"Extracting job description from URL: {url}")
    
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            logger.info(f"Fetching URL with timeout={timeout}s")
            response = client.get(url)
            response.raise_for_status()
            html = response.text
            logger.info(f"URL fetched successfully ({len(html)} chars)")

        soup = BeautifulSoup(html, "lxml")

        # Strategy 1: JSON-LD
        logger.info("Attempting JSON-LD extraction")
        description = _extract_from_json_ld(soup)
        if description:
            logger.info(f"✅ Job description extracted via JSON-LD ({len(description)} chars)")
            return description

        # Strategy 2: Readability
        logger.info("Attempting readability extraction")
        doc = Document(html)
        article_html = doc.summary(html_partial=True)
        article_text = _clean_html(article_html)
        if _meaningful(article_text):
            logger.info(f"✅ Job description extracted via readability ({len(article_text)} chars)")
            return article_text

        # Strategy 3: Trafilatura
        logger.info("Attempting trafilatura extraction")
        traf_text = trafilatura.extract(html, favor_precision=True)
        if _meaningful(traf_text):
            logger.info(f"✅ Job description extracted via trafilatura ({len(traf_text)} chars)")
            return traf_text

        # Strategy 4: Heuristics
        logger.info("Attempting heuristic extraction")
        heuristic_result = _heuristic_extract(soup)
        if heuristic_result:
            logger.info(f"✅ Job description extracted via heuristics ({len(heuristic_result)} chars)")
            return heuristic_result
        
        logger.warning(f"No meaningful job description found for URL: {url}")
        return None
    
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error fetching URL {url}: {e.response.status_code}", exc_info=True)
        raise
    except httpx.TimeoutException as e:
        logger.error(f"❌ Timeout fetching URL {url}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"❌ Failed to extract job description from URL {url}: {e}", exc_info=True)
        raise


def _extract_from_json_ld(soup: BeautifulSoup) -> Optional[str]:
    logger.info("Searching for JSON-LD job posting data")
    
    try:
        script_count = 0
        for script in soup.find_all("script", type="application/ld+json"):
            script_count += 1
            try:
                payload = json.loads(script.string or "")
            except json.JSONDecodeError:
                logger.info(f"Skipping invalid JSON in script tag #{script_count}")
                continue

            data_items = payload if isinstance(payload, list) else [payload]
            for item in data_items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") == "JobPosting":
                    description = item.get("description")
                    if description:
                        logger.info(f"Found JobPosting in JSON-LD (script #{script_count})")
                        return _clean_html(description)
                if "@graph" in item and isinstance(item["@graph"], list):
                    for sub_item in item["@graph"]:
                        if isinstance(sub_item, dict) and sub_item.get("@type") == "JobPosting":
                            description = sub_item.get("description")
                            if description:
                                logger.info(f"Found JobPosting in JSON-LD @graph (script #{script_count})")
                                return _clean_html(description)
        
        logger.info(f"No JobPosting found in {script_count} JSON-LD script(s)")
        return None
    
    except Exception as e:
        logger.error(f"❌ Error extracting from JSON-LD: {e}", exc_info=True)
        return None


def _heuristic_extract(soup: BeautifulSoup) -> Optional[str]:
    logger.info("Attempting heuristic extraction with CSS selectors")
    
    try:
        selectors = [
            "#jobDescriptionText",
            ".jobDescriptionText",
            "#jobDescription",
            ".job-description",
            ".jobs-description__content",
            "[data-testid='jobDescription']",
            "[itemprop='description']",
            "article",
        ]
        
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = _clean_html(str(node))
                if _meaningful(text):
                    logger.info(f"Heuristic match found with selector: {selector}")
                    return text
        
        logger.info("No heuristic selector matched")
        return None
    
    except Exception as e:
        logger.error(f"❌ Error in heuristic extraction: {e}", exc_info=True)
        return None


def _clean_html(fragment: str) -> str:
    soup = BeautifulSoup(fragment or "", "lxml")
    for bad in soup(["script", "style", "noscript", "footer", "header", "nav"]):
        bad.extract()
    parts = list(soup.stripped_strings)
    return "\n".join(parts)


def _meaningful(text: Optional[str], *, min_words: int = 50) -> bool:
    if not text:
        return False
    word_count = len(text.split())
    return word_count >= min_words