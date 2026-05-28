"""
物件リストCSVから住所抽出・ジオコーディング(国土地理院API)→ properties.json生成
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

INPUT_CSV = "/Users/ryonagao/Downloads/②加工_2024~2025_竣工物件リスト (data) (1).csv"
OUTPUT_JSON = Path(__file__).parent / "data" / "properties.json"
OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Cache file to avoid re-geocoding
CACHE_FILE = Path(__file__).parent / "data" / "geocode_cache.json"
cache = {}
if CACHE_FILE.exists():
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

def geocode_gsi(address: str):
    """国土地理院ジオコーディングAPI"""
    if address in cache:
        return cache[address]
    url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={urllib.parse.quote(address)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            if data and len(data) > 0:
                coords = data[0]["geometry"]["coordinates"]
                result = {"lng": coords[0], "lat": coords[1], "matched": data[0].get("properties", {}).get("title", "")}
                cache[address] = result
                return result
    except Exception as e:
        print(f"  geocode error: {address} -> {e}")
    cache[address] = None
    return None

# Read CSV
properties = []
with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    # Build header map (CSVは重複ヘッダーあり)
    for i, row in enumerate(reader):
        # Pick first occurrence of each key
        都道府県 = row.get("都道府県", "") or ""
        市区町村 = row.get("市区町村", "") or ""
        町丁目 = row.get("町丁目", "") or ""
        住居表示 = row.get("住居表示", "") or ""
        # Address composite
        address = f"{都道府県}{市区町村}{町丁目}{住居表示}".strip()
        if not address or address == "":
            continue
        properties.append({
            "id": i,
            "建物番号": row.get("建物番号", ""),
            "物件名": row.get("物件名", "") or row.get("建物名", ""),
            "事業主": row.get("事業主", "") or row.get("全事業主", ""),
            "総戸数": row.get("総戸数", ""),
            "平均価格": row.get("平均価格", ""),
            "平均坪単価": row.get("平均坪単価", ""),
            "最寄駅": row.get("最寄駅", ""),
            "徒歩": row.get("徒歩", ""),
            "竣工日": row.get("竣工日", ""),
            "都道府県": 都道府県,
            "市区町村": 市区町村,
            "住所": address,
            "lat": None,
            "lng": None,
        })

print(f"Total properties (raw): {len(properties)}")

# Geocode
geocoded = 0
for i, p in enumerate(properties):
    if not p["住所"]:
        continue
    result = geocode_gsi(p["住所"])
    if result:
        p["lat"] = result["lat"]
        p["lng"] = result["lng"]
        p["matched_address"] = result.get("matched", "")
        geocoded += 1
    if (i + 1) % 50 == 0:
        print(f"  progress: {i+1}/{len(properties)} (geocoded: {geocoded})")
        # Save cache periodically
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    # Throttle
    if result is None or p["住所"] not in cache or not cache[p["住所"]]:
        time.sleep(0.3)
    else:
        # Already cached, no API hit
        pass

# Final save
CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Geocoded: {geocoded}/{len(properties)}")

# Filter out non-geocoded for final output (keep all but geocoded coord may be None)
OUTPUT_JSON.write_text(json.dumps(properties, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved: {OUTPUT_JSON}")
