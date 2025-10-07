import os
import re
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
load_dotenv()

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN env var not set.")

HF_MODEL = os.environ.get("HF_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")

# Initializing HF client
hf_client = InferenceClient(token=HF_TOKEN)

app = Flask(__name__)
CORS(app)

def repair_json(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    m = re.search(r"(\[.*\])", text, re.DOTALL)  # Expect array
    if m:
        text = m.group(0)
    text = text.replace("'", '"')
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text

def parse_model_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        repaired = repair_json(text)
        try:
            return json.loads(repaired)
        except Exception:
            return None

def build_prompt(ingredients: list) -> str:
    ingredients_str = ", ".join(f'"{ing}"' for ing in ingredients)
    example = '[{"ingredient":"X","description":"...","healthy":"Yes","reason":"...","banned_in":[],"rating":4}]'
    if len(ingredients) > 1:
        example = '[{"ingredient":"X","description":"...","healthy":"Yes","reason":"...","banned_in":[],"rating":4}, {"ingredient":"Y","description":"...","healthy":"No","reason":"...","banned_in":["USA"],"rating":2}]'
    
    return f"""
You are an expert nutrition and food-ingredients analyst.

Analyze these ingredients: {ingredients_str}

Return a JSON array of objects (no surrounding commentary), each with the following fields:
- ingredient: string (the original ingredient)
- description: short description (what it is and why used)
- healthy: "Yes" or "No" or "Unknown"
- reason: brief explanation for the healthy judgement
- banned_in: array of country names where it is banned or restricted (empty array if none)
- rating: integer 1..5 (1 worst, 5 best)

Example:
{example}

Return only valid JSON (array). Keep answers concise.
"""

@app.route("/analyze", methods=["POST"])
def analyze():
    payload = request.json or {}
    ingredients = payload.get("ingredients", [])
    if not ingredients:
        return jsonify({"error": "Missing 'ingredients' in request body"}), 400

    prompt = build_prompt(ingredients)

    try:
        resp = hf_client.chat_completion(
            model=HF_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000  
        )
        result_text = resp.choices[0].message.content
    except Exception as e:
        return jsonify({
            "results": [
                {
                    "ingredient": ing,
                    "description": None,
                    "healthy": "Unknown",
                    "reason": f"Model call failed: {str(e)}",
                    "banned_in": [],
                    "rating": None,
                    "parse_status": "model_error",
                    "raw_output": None
                } for ing in ingredients
            ]
        }), 500

    parsed = parse_model_json(result_text)

    if isinstance(parsed, list):
        results = []
        ingredient_set = set(ingredients)
        for item in parsed:
            if not isinstance(item, dict):
                continue
            ingredient = item.get("ingredient")
            if ingredient not in ingredient_set:
                continue
            description = item.get("description") or ""
            healthy = item.get("healthy") or item.get("safe") or "Unknown"
            reason = item.get("reason") or item.get("explanation") or ""
            banned = item.get("banned_in") or item.get("banned") or []
            rating = item.get("rating")
            if not isinstance(banned, list):
                banned = [banned] if banned else []
            try:
                rating = int(rating) if rating is not None else None
            except Exception:
                rating = None
            results.append({
                "ingredient": ingredient,
                "description": description,
                "healthy": healthy,
                "reason": reason,
                "banned_in": banned,
                "rating": rating,
                "parse_status": "ok",
                "raw_output": result_text
            })
        for ing in ingredients:
            if not any(r["ingredient"] == ing for r in results):
                results.append({
                    "ingredient": ing,
                    "description": None,
                    "healthy": "Unknown",
                    "reason": "Ingredient not in AI response",
                    "banned_in": [],
                    "rating": None,
                    "parse_status": "missing",
                    "raw_output": result_text
                })
        return jsonify({"results": results}), 200
    elif isinstance(parsed, dict):
        # If model returns single object, wrap in list
        return analyze()  # Retry or handle, but for simplicity, treat as list of one
    else:
        return jsonify({
            "results": [
                {
                    "ingredient": ing,
                    "description": None,
                    "healthy": "Unknown",
                    "reason": "Model did not return parseable JSON",
                    "banned_in": [],
                    "rating": None,
                    "parse_status": "parse_failed",
                    "raw_output": result_text
                } for ing in ingredients
            ]
        }), 200

if __name__ == "__main__":
    print("AI service running on http://localhost:5002 — endpoint POST /analyze")
    app.run(debug=True, port=5002)