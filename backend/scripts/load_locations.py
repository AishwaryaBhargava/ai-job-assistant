# scripts/load_locations.py
import csv
import asyncio
from database import locations_collection
from services.ai_service import embed_for_matching
from utils.logger import logger  # ✅ Added logger

async def load_locations():
    logger.info("Starting location loading process")
    
    try:
        # Clean slate
        logger.info("Deleting existing locations from database")
        delete_result = await locations_collection.delete_many({})
        logger.info(f"Deleted {delete_result.deleted_count} existing locations")

        cities = []
        logger.info("Reading locations from data/locations.csv")
        
        try:
            with open("data/locations.csv", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = f"{row['city']}, {row['country']}"
                    cities.append(name)
            
            logger.info(f"Successfully read {len(cities)} cities from CSV")
        
        except FileNotFoundError as e:
            logger.error(f"❌ CSV file not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"❌ Failed to read CSV file: {e}", exc_info=True)
            raise

        # Batch embeddings
        batch_size = 50
        logger.info(f"Starting batch embedding process with batch_size={batch_size}")
        
        for i in range(0, len(cities), batch_size):
            batch = cities[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(cities)-1)//batch_size + 1} ({len(batch)} cities)")
            
            try:
                vectors = embed_for_matching(batch)
                docs = [{"name": name, "embedding": vec} for name, vec in zip(batch, vectors)]
                await locations_collection.insert_many(docs)
                print(f"Inserted {len(docs)} locations")
                logger.info(f"✅ Successfully inserted {len(docs)} locations (batch {i//batch_size + 1})")
            
            except Exception as e:
                logger.error(f"❌ Failed to process batch {i//batch_size + 1}: {e}", exc_info=True)
                raise

        logger.info(f"✅ Location loading completed successfully. Total locations loaded: {len(cities)}")

    except Exception as e:
        logger.error(f"❌ Location loading process failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Script started: load_locations.py")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(load_locations())
        logger.info("✅ Script completed successfully")
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}", exc_info=True)
        raise