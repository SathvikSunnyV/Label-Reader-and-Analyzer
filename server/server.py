import os
import requests
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MongoDB config
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "label_reader")
ALTERNATIVES_COLLECTION = os.environ.get("ALTERNATIVES_COLLECTION", "alternatives")

# AI service endpoint
AI_URL = os.environ.get("AI_URL", "http://localhost:5002/analyze")

# Initialize Mongo client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
alternatives_collection = db[ALTERNATIVES_COLLECTION]

@app.route('/process_ingredients', methods=['POST'])
def process_ingredients():
    data = request.json or {}
    ingredients = data.get('ingredients', [])
    product_type = data.get('product_type')

    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    # Send all ingredients to AI service in one request
    try:
        ai_resp = requests.post(AI_URL, json={"ingredients": ingredients}, timeout=30)
        ai_resp.raise_for_status()
        ai_data = ai_resp.json()
        results = ai_data.get("results", [])
    except Exception as e:
        results = [
            {
                "ingredient": ing,
                "usage": "Usage not available (AI call failed)",
                "health": {"verdict": "Error", "reason": f"AI call failed: {str(e)}"},
                "banned_countries": [],
                "raw_ai_response": None
            } for ing in ingredients
        ]

    # Normalize AI results to match expected frontend format
    normalized_results = []
    for result in results:
        normalized_results.append({
            "ingredient": result.get("ingredient"),
            "usage": result.get("description") or "Description not provided",
            "health": {
                "verdict": result.get("healthy") or "Unknown",
                "reason": result.get("reason") or "",
                "rating": result.get("rating")
            },
            "banned_countries": result.get("banned_in") or [],
            "raw_ai_response": result.get("raw_output")
        })

    response = {"results": normalized_results}

    # Fetch alternatives from MongoDB if product_type provided
    if product_type:
        try:
            alt_doc = alternatives_collection.find_one({"type": product_type.lower()})
            response["alternatives"] = alt_doc.get("alternatives", []) if alt_doc else []
        except Exception as e:
            response["alternatives"] = []
            response["warning"] = f"MongoDB query failed: {str(e)}"

    return jsonify(response), 200

@app.route('/add_alternatives', methods=['POST'])
def add_alternatives():
    data = request.json or {}
    product_type = data.get('type')
    alts = data.get('alternatives', [])

    if not product_type or not alts:
        return jsonify({"error": "Missing type or alternatives"}), 400

    try:
        alternatives_collection.update_one(
            {"type": product_type.lower()},
            {"$set": {"alternatives": alts}},
            upsert=True
        )
        return jsonify({"message": "Alternatives added/updated"}), 200
    except Exception as e:
        return jsonify({"error": f"MongoDB update failed: {str(e)}"}), 500

if __name__ == '__main__':
    print("Main backend running on http://localhost:5000")
    app.run(debug=True, port=5000)