**Scraping Documentation**
I have build a scraper which currently fetches from multiple websites like wikipedia , pubchem ,open food facts etc
this scraper is build as a fastapi which fetches required data from the websites api's

🔹 Requirements for Scraper

Python packages:

fastapi          # Web framework for building the API
uvicorn          # ASGI server to run FastAPI
requests         # To fetch data from OpenFoodFacts, PubChem
wikipedia-api    # To fetch ingredient details from Wikipedia


🔹 Complete Flow of the Scraper

1.Input (from backend/frontend)

   Expects a POST request at /scrape

2.JSON body:

   Processing

   For each ingredient:

   Normalize name (remove symbols, brackets, E-numbers).

3.Fetch data:

   Wikipedia → summary + banned info

   OpenFoodFacts → ingredient tags

   PubChem → chemical description

4.Cross-check banned countries:

   Extracted from Wikipedia text

   Add curated banned list (fallback data).

   Merge results into one enriched record.

   Output (Response)

5.Returns JSON with results list:
