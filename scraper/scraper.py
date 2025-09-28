from fastapi import FastAPI
from pydantic import BaseModel
import requests
import wikipediaapi
import re
import uvicorn

# Initialize Wikipedia with proper user-agent
wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent='LabelReaderScraper/1.0 (dasaribhuvan305@gmail.com)'
)

# Create FastAPI app
app = FastAPI()

# Curated banned list (fallback for regulatory data)
CURATED_BANNED = {
    "ractopamine": ["China", "Russia", "EU"],
    "potassium bromate": ["India", "EU", "Canada"],
    "azodicarbonamide": ["Australia", "EU"]
}

# Request model
class RequestData(BaseModel):
    ingredients: list[str]

# Normalize ingredient names
def normalize(ingredient: str) -> str:
    s = ingredient.lower()
    s = re.sub(r"\bE\d+\b", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^a-z\s]", "", s)
    return s.strip()

# Extract banned countries from text
def parse_banned(text: str) -> list[str]:
    banned = []
    if not text:
        return banned
    pattern = r"banned in ([A-Z][a-zA-Z ,and]+)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    for m in matches:
        parts = re.split(r",| and ", m)
        banned.extend([p.strip() for p in parts if p.strip()])
    return list(set(banned))

# Fetch Wikipedia description and banned countries
def fetch_wikipedia(ingredient: str):
    page = wiki.page(ingredient)
    if not page.exists():
        return None, None
    summary_lines = page.summary.split(". ")
    description = ". ".join(summary_lines[:3])  # ~3-4 lines
    banned = parse_banned(page.text)
    return description, banned

# Fetch OpenFoodFacts tags for additional context
def fetch_openfoodfacts(ingredient: str):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={ingredient}&search_simple=1&action=process&json=1&page_size=1"
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        if 'products' in data and data['products']:
            product = data['products'][0]
            tags = product.get('ingredients_tags', [])
            return ", ".join(tags)[:300]
    except:
        return None

# Fetch PubChem description (optional, chemical context)
def fetch_pubchem(ingredient: str):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{ingredient}/description/JSON"
        res = requests.get(url, timeout=5)
        data = res.json()
        if 'InformationList' in data and 'Information' in data['InformationList']:
            info = data['InformationList']['Information'][0]
            desc = info.get('Description', '')
            return desc[:400]  # up to ~3-4 lines
    except:
        return None

# Merge info from all sources
def enrich_ingredient(ingredient: str):
    normalized = normalize(ingredient)

    desc_wiki, banned_wiki = fetch_wikipedia(normalized)
    desc_off = fetch_openfoodfacts(normalized)
    desc_pub = fetch_pubchem(normalized)

    # Merge descriptions
    descriptions = [d for d in [desc_wiki, desc_off, desc_pub] if d]
    description = " ".join(descriptions) or "No description available."

    # Merge banned countries
    banned = banned_wiki or []
    banned += CURATED_BANNED.get(normalized, [])
    banned = list(set(banned))

    # Track sources
    sources = []
    if desc_wiki: sources.append("Wikipedia")
    if desc_off: sources.append("OpenFoodFacts")
    if desc_pub: sources.append("PubChem")
    if normalized in CURATED_BANNED: sources.append("Curated")

    return {
        "ingredient": ingredient,
        "description": description.strip(),
        "banned_in": banned,
        "sources": sources
    }

# FastAPI endpoint
@app.post("/scrape")
def scrape(data: RequestData):
    results = [enrich_ingredient(i) for i in data.ingredients]
    return {"results": results}

# Run server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
