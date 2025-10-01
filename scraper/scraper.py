#!/usr/bin/env python3
# scraper.py -- Ingredient lookup with DDG + Wikipedia fallback
#
# Behavior:
# - INS/E codes: fallback table  -> wikipedia summary (if needed)
# - Non-INS: DuckDuckGo API -> Wikipedia Summary API -> Wikipedia HTML scrape
# - Short, food-focused descriptions; dynamic handling of "turmeric powder" style names

import sys, json, re, time, requests, random
from bs4 import BeautifulSoup
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

# ---- Config ----
DDG_API_TIMEOUT = 20
WIKI_TIMEOUT = 10
MAX_DESC_CHARS = 400
MAX_WORKERS = 6
DDG_RETRY = 4
WIKI_RETRY = 3
DEBUG = False   # set True to see network/parse errors

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"
]

# ---- Helpers ----
def clean_text(s: str):
    if not s:
        return ""
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\[[^\]]*\]', '', s)
    return s.strip()

def normalize_key(s: str) -> str:
    return re.sub(r'\s+', ' ', unescape(str(s or "").strip().lower()))

def get_with_retries(url, params=None, timeout=10, tries=3):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    last_exc = None
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
        except Exception as e:
            last_exc = e
            time.sleep(1.2 * (attempt + 1))
    if last_exc and DEBUG:
        print(f"Request failed {url}: {last_exc}", file=sys.stderr)
    return None

def first_sentences(text, n=2):
    if not text:
        return ""
    sentences = text.split(". ")
    out = ". ".join(sentences[:n]).strip()
    if not out.endswith("."):
        out += "."
    return out

# ---- Heuristics ----
def looks_like_food_use(text: str) -> bool:
    """Return True if text contains food/use words (helps avoid botanical-only summaries)."""
    if not text:
        return False
    kws = ["food", "used in", "cooking", "ingredient", "additive", "seasoning",
           "flavour", "flavor", "preservative", "spice", "culinary", "color", "colour",
           "sweetener", "thickener", "oil", "flour", "dye", "coloring", "used as"]
    t = text.lower()
    return any(k in t for k in kws)

def normalize_query_variants(q: str):
    """Yield query variants to try (strip common suffixes like 'powder', 'flour')."""
    q = q.strip()
    yield q
    # common suffixes to remove (helpful for 'Turmeric Powder' -> 'Turmeric')
    suffixes = ["powder", "powdered", "flour", "meal", "extract", "oil", "powder", "crushed"]
    for s in suffixes:
        if q.lower().endswith(" " + s):
            yield q[:-(len(s)+1)]
    # also try singular/plural toggles (very basic)
    if q.endswith("s"):
        yield q[:-1]
    else:
        yield q + "s"

# ---- Wikipedia Summary API (tries variants) ----
def wikipedia_summary(query):
    if not query:
        return ""
    for q in normalize_query_variants(query):
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(q.replace(' ', '_'))}"
        r = get_with_retries(url, timeout=WIKI_TIMEOUT, tries=WIKI_RETRY)
        if not r or r.status_code != 200:
            continue
        try:
            data = r.json()
            extract = clean_text(data.get("extract", "") or "")
            if extract:
                return first_sentences(extract, 2)
        except Exception as e:
            if DEBUG:
                print(f"Wikipedia summary parse error for {q}: {e}", file=sys.stderr)
            continue
    return ""

# ---- Wikipedia HTML fallback (last resort) ----
def wikipedia_fallback(query):
    if not query:
        return ""
    for q in normalize_query_variants(query):
        url = f"https://en.wikipedia.org/wiki/{quote(q.replace(' ', '_'))}"
        r = get_with_retries(url, timeout=WIKI_TIMEOUT, tries=WIKI_RETRY)
        if not r:
            continue
        try:
            soup = BeautifulSoup(r.text, "html.parser")
            # Prefer first paragraphs that mention food usage
            paras = soup.find_all("p")[:6]
            for p in paras:
                txt = clean_text(p.get_text(" ", strip=True))
                if not txt:
                    continue
                if looks_like_food_use(txt) or len(txt) > 40:
                    return first_sentences(txt, 2)[:MAX_DESC_CHARS]
        except Exception as e:
            if DEBUG:
                print(f"Wikipedia HTML parse error for {q}: {e}", file=sys.stderr)
            continue
    return ""

# ---- DuckDuckGo API snippet ----
def ddg_api_snippet(query):
    # Attempt several contextual queries
    queries = [
        f"{query} food additive", f"{query} ingredient", f"{query} food use",
        f"{query} cooking", f"{query} edible", f"{query} seasoning"
    ]
    for q in queries:
        url = f"https://api.duckduckgo.com/?q={quote(q)}&format=json&no_html=1"
        r = get_with_retries(url, timeout=DDG_API_TIMEOUT, tries=DDG_RETRY)
        if not r:
            continue
        try:
            data = r.json()
            # Prefer Abstract or Answer
            for key in ("Abstract", "Answer", "Definition", "AbstractText"):
                txt = clean_text(data.get(key, "") or "")
                if txt and looks_like_food_use(txt):
                    return first_sentences(txt, 2)[:MAX_DESC_CHARS]
            # Try related topics
            for topic in data.get("RelatedTopics", []):
                if isinstance(topic, dict):
                    txt = clean_text(topic.get("Text", "") or "")
                    if txt and looks_like_food_use(txt):
                        return first_sentences(txt, 2)[:MAX_DESC_CHARS]
        except Exception:
            # silent fail; fallback will handle
            if DEBUG:
                print(f"DDG parse error for query: {q}", file=sys.stderr)
            continue
    return ""

# ---- INS/E utilities (fallback table) ----
def numeric_ins_from_token(token: str):
    m = re.search(r'(?:E|INS)\s*(\d+)', token, re.I)
    return m.group(1) if m else None

# Small fallback INS map (can be expanded or populated dynamically later)
FALLBACK_INS = {
    "621": {"name": "Monosodium glutamate", "function": "flavour enhancer", "approved": "USA, European Union, India"},
    "330": {"name": "Citric acid", "function": "food acid", "approved": "USA, European Union, India"},
}

def build_ins_description(entry: dict, ins_num: str):
    name = entry.get("name", f"INS {ins_num}")
    function = entry.get("function", "food additive")
    approved = entry.get("approved", "various countries")
    return f"{name} (INS {ins_num}). is used as {function}. Approved in: {approved}"

# ---- lookup_one (fixed indentation & dynamic summary check) ----
def lookup_one(ingredient, ins_data, banned_lookup):
    orig = str(ingredient or "").strip()
    canonical = normalize_key(orig)
    out = {
        "Ingredient": orig,
        "Canonical_Name": canonical,
        "Description": "",
        "Sources": "None",
        "Banned_In": "None"
    }

    if not orig:
        return out

    # banned lookup (if provided)
    v = banned_lookup.get(canonical) or banned_lookup.get(re.sub(r'[\s\-]+', '', canonical))
    if v:
        out["Banned_In"] = v

    # Case 1: INS/E codes
    ins_num = numeric_ins_from_token(orig)
    if ins_num:
        entry = ins_data.get(ins_num) or FALLBACK_INS.get(ins_num)
        if entry:
            out["Description"] = build_ins_description(entry, ins_num)
            out["Sources"] = "Wikipedia INS" if ins_data.get(ins_num) else "Fallback"
            name_key = normalize_key(entry.get("name", ""))
            if name_key in banned_lookup:
                out["Banned_In"] = banned_lookup[name_key]
            return out
        out["Description"] = "No food-specific data available."
        return out

    # Case 2: DuckDuckGo (first attempt)
    ddg_text = ddg_api_snippet(orig)
    if ddg_text:
        out["Description"] = first_sentences(ddg_text, 2)[:MAX_DESC_CHARS]
        out["Sources"] = "DuckDuckGo"
        return out

    # Case 3: Wikipedia Summary (but if summary is non-culinary, fallback to HTML)
    summary = wikipedia_summary(orig)
    if summary:
        if looks_like_food_use(summary):
            out["Description"] = first_sentences(summary, 2)[:MAX_DESC_CHARS]
            out["Sources"] = "Wikipedia Summary"
            return out
        # summary exists but doesn't mention food use -> try HTML fallback
        fallback_txt = wikipedia_fallback(orig)
        if fallback_txt:
            out["Description"] = first_sentences(fallback_txt, 2)[:MAX_DESC_CHARS]
            out["Sources"] = "Wikipedia (HTML Fallback)"
            return out

    # Case 4: HTML fallback (last resort)
    fallback = wikipedia_fallback(orig)
    if fallback:
        out["Description"] = first_sentences(fallback, 2)[:MAX_DESC_CHARS]
        out["Sources"] = "Wikipedia (HTML Fallback)"
        return out

    # Nothing found
    out["Description"] = "No food-specific data available."
    return out

# ---- Main ----
def main():
    try:
        raw = sys.stdin.read()
        if not raw:
            user = input("Enter comma-separated ingredients: ").strip()
            data = {"ingredients": [w.strip() for w in user.split(",") if w.strip()]}
        else:
            data = json.loads(raw)
    except Exception as e:
        print(json.dumps({"error": f"Invalid input: {e}"}))
        return

    ingredients = data.get("ingredients", [])
    ins_data = {}        # placeholder: could be populated by scraping the INS table if desired
    banned_lookup = {}   # optional banned ingredients map

    results = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(ingredients) or 1)) as ex:
        futures = {ex.submit(lookup_one, ing, ins_data, banned_lookup): ing for ing in ingredients}
        for fut in as_completed(futures):
            results.append(fut.result())

    # preserve order
    res_map = {r["Ingredient"]: r for r in results}
    ordered = [res_map.get(i, {"Ingredient": i, "Canonical_Name": normalize_key(i),
                               "Description": "No data", "Sources": "None"}) for i in ingredients]

    print(json.dumps({"results": ordered}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
