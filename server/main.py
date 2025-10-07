import os
import requests
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "label_reader")
INGREDIENTS_COLLECTION = os.environ.get("INGREDIENTS_COLLECTION", "ingredients")

# AI model endpoint
AI_URL = os.environ.get("AI_URL", "http://localhost:5002/analyze")

# Initializing Mongo client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
ingredients_collection = db[INGREDIENTS_COLLECTION]

@app.route('/process_ingredients', methods=['POST'])
def process_ingredients():
    data = request.json or {}
    ingredients = data.get('ingredients', [])

    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    # Normalize ingredients to lowercase for caching/lookup
    lower_to_original = {ing.lower(): ing for ing in ingredients}

    # Find cached ingredients
    cached_results = {}
    missing = []
    for ing in ingredients:
        lower_ing = ing.lower()
        cached = ingredients_collection.find_one({"_id": lower_ing})
        if cached:
            cached_results[ing] = cached['data']
        else:
            missing.append(ing)

    ai_normalized = []
    if missing:
        try:
            ai_resp = requests.post(AI_URL, json={"ingredients": missing}, timeout=30)
            ai_resp.raise_for_status()
            ai_data = ai_resp.json()
            ai_results = ai_data.get("results", [])
            
            for result in ai_results:
                normalized = {
                    "ingredient": result.get("ingredient"),
                    "usage": result.get("description") or "Description not provided",
                    "health": {
                        "verdict": result.get("healthy") or "Unknown",
                        "reason": result.get("reason") or "",
                        "rating": result.get("rating")
                    },
                    "banned_countries": result.get("banned_in") or [],
                    "raw_ai_response": result.get("raw_output")
                }
                ai_normalized.append(normalized)
                
                # Cache the normalized result
                lower = normalized['ingredient'].lower()
                ingredients_collection.update_one(
                    {"_id": lower},
                    {"$set": {"data": normalized}},
                    upsert=True
                )
        except Exception as e:
            for ing in missing:
                normalized = {
                    "ingredient": ing,
                    "usage": "Usage not available (AI call failed)",
                    "health": {"verdict": "Error", "reason": f"AI call failed: {str(e)}"},
                    "banned_countries": [],
                    "raw_ai_response": None
                }
                ai_normalized.append(normalized)
                # Optionally cache errors, but here we skip caching errors to avoid persisting failures

    # Combine results in the order of input ingredients
    normalized_results = []
    ai_map = {norm['ingredient']: norm for norm in ai_normalized}
    for ing in ingredients:
        if ing in cached_results:
            normalized_results.append(cached_results[ing])
        elif ing in ai_map:
            normalized_results.append(ai_map[ing])
        else:
            # Fallback if somehow missing
            normalized_results.append({
                "ingredient": ing,
                "usage": "Usage not available",
                "health": {"verdict": "Unknown", "reason": "Not found in AI response"},
                "banned_countries": [],
                "raw_ai_response": None
            })

    response = {"results": normalized_results}
    return jsonify(response), 200

if __name__ == '__main__':
    print("Main backend running on http://localhost:5000")
    app.run(debug=True, port=5000)