from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
### using cors for frontend requests 
CORS(app)  

### connecting to MongoDB
client = MongoClient("mongodb://localhost:27017/")  
db = client["label_reader"]
alternatives_collection = db["alternatives"]

## update with actual end points 
SCRAPER_URL = "http://localhost:5001/scrape"  
AI_URL = "http://localhost:5002/analyze" 

### handling post request from frontend for processing ingredients
@app.route('/process_ingredients', methods=['POST'])
def process_ingredients():
    data = request.json
    ingredients = data.get('ingredients', [])
    product_type = data.get('product_type', None) 
    
    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400
    
    results = []
    for ing in ingredients:
        ## calling scraper module
        try:
            scraper_response = requests.post(SCRAPER_URL, json={"ingredients": [ing]})
            scraper_response.raise_for_status()
            scraper_data = scraper_response.json()

            if scraper_data.get("results"):
              first_result = scraper_data["results"][0]
              usage = first_result.get("description", "Usage not available")
              banned_countries = first_result.get("banned_in", [])
            else:
              usage = "Usage not available"
              banned_countries = []

        except Exception as e:
            usage = f"Scraper error: {str(e)}"
            banned_countries = []
        
        ## calling AI module
        try:
            ai_response = requests.post(AI_URL, json={"ingredient": ing})
            ai_response.raise_for_status()
            ai_data = ai_response.json()
            health = {
                "verdict": ai_data.get("verdict", "Unknown"),
                "reason": ai_data.get("reason", "Reason not available")
            }
        except Exception as e:
            health = {"verdict": "Error", "reason": f"AI error: {str(e)}"}
        
        results.append({
            "ingredient": ing,
            "usage": usage,
            "health": health,
            "banned_countries": banned_countries
        })
### response object to be returned
    response = {"results": results}
    
    if product_type:
        alternatives = []
        alt_doc = alternatives_collection.find_one({"type": product_type.lower()})
        if alt_doc:
            alternatives = alt_doc.get("alternatives", [])
        response["alternatives"] = alternatives
    
    return jsonify(response)


### handling post requests from frontend for addingalternatives 
@app.route('/add_alternatives', methods=['POST'])
def add_alternatives():
    """Endpoint to add healthy alternatives (for data population)."""
    data = request.json
    product_type = data.get('type')
    alts = data.get('alternatives', [])
    
    if not product_type or not alts:
        return jsonify({"error": "Missing type or alternatives"}), 400
    
    alternatives_collection.update_one(
        {"type": product_type.lower()},
        {"$set": {"alternatives": alts}},
        upsert=True
    )
    return jsonify({"message": "Alternatives added/updated"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)  
    print("App is running on http://localhost:5000")
