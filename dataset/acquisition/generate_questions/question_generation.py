import json
import requests
import configparser


cfg = configparser.ConfigParser()
cfg.read("config.ini")
base_url = cfg["DEFAULT"]["base_url"]
model_name = cfg["DEFAULT"]["model_name"]
auth = cfg["DEFAULT"].get("authorization_token", "").strip()

with open("dataset/acquisition/generate_questions/trend_prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

body = {
    "model": model_name,
    "prompt": prompt,
    "stream": False,
    "format": {
        "type": "object",
        "properties": {
            "qnaList": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "questions": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["category", "questions"]
                }
            }
        },
        "required": ["qnaList"]
    }
}

headers = {"Content-Type": "application/json"}
if auth:
    headers["Authorization"] = f"Bearer {auth}"

resp = requests.post(base_url, headers=headers, json=body, timeout=120)
print("Status:", resp.status_code)
resp.raise_for_status()


raw_text = resp.text
try:
    data = resp.json()
except json.JSONDecodeError:
    data = raw_text

if isinstance(data, str):
    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        data = {}

qna_list = []


nested = data["response"]
if isinstance(nested, str):
    try:
        nested = json.loads(nested)
    except json.JSONDecodeError:
        nested = {}
if isinstance(nested, dict) and isinstance(nested.get("qnaList"), list):
    qna_list = nested["qnaList"]


def normalize_qna(qna_list):
    cleaned = []
    if not isinstance(qna_list, list):
        return cleaned

    for item in qna_list:
        if not isinstance(item, dict):
            continue

        if "q" in item:
            q = str(item.get("q", "")).replace("\n", " ").replace("\t", " ").strip()
            if q:
                cleaned.append({"q": q})
            continue

        if "category" in item and isinstance(item.get("questions"), list):
            category = str(item.get("category", "")).strip()
            for q in item["questions"]:
                q = str(q).replace("\n", " ").replace("\t", " ").strip()
                if q:
                    cleaned.append({"category": category, "q": q})

    return cleaned

cleaned = normalize_qna(qna_list)

if cleaned:
    with open("qna.json", "w", encoding="utf-8") as f:
        json.dump({"qnaList": cleaned}, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(cleaned)} questions to qna.json")
else:
    print("Could not find qnaList items. Saving raw response to debug_response.json for inspection.")
    with open("debug_response.json", "w", encoding="utf-8") as f:
        f.write(raw_text[:200000])