import csv
from pathlib import Path
from typing import List
from utils.logger import logger

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "locations.csv"
_locations: List[str] = []


def load_locations_from_csv(force: bool = False) -> List[str]:
    """Load all locations from CSV into memory."""
    global _locations

    if force or not _locations:
        logger.info("Loading locations from CSV...")
        _locations = []

        if not DATA_PATH.exists():
            logger.error(f"locations.csv not found at {DATA_PATH}")
            raise FileNotFoundError(f"locations.csv not found at {DATA_PATH}")

        try:
            with open(DATA_PATH, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    city = row.get("city_ascii") or row.get("city")
                    country = row.get("country")
                    if city:
                        label = f"{city.strip()}, {country.strip()}" if country else city.strip()
                        _locations.append(label)
            logger.info(f"Loaded {len(_locations)} locations from {DATA_PATH}")
        except Exception as exc:
            logger.exception(f"Failed to load locations: {exc}")
            raise

    return _locations


def search_locations(query: str, limit: int = 8) -> List[str]:
    """Search cached locations for a partial query match."""
    if not _locations:
        logger.warning("Locations cache empty — reloading CSV.")
        load_locations_from_csv()

    q = query.lower().strip()
    results = [loc for loc in _locations if q in loc.lower()]
    logger.info(f"Found {len(results)} matches for query='{query}' (limit={limit})")
    return results[:limit]
