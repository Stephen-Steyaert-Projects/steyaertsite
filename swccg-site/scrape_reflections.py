import re
import time
import urllib.request

BASE_URL = "https://www.categoryonegames.com/catalog/star_wars_ccg-reflections_i/439?page={}&sort_by_price=0"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

names = []

for page in range(1, 6):
    url = BASE_URL.format(page)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        html = response.read().decode("utf-8")

    found = re.findall(r'<h4[^>]*itemprop="name"[^>]*title="([^"]+)"', html)
    print(f"Page {page}: {len(found)} cards")
    names.extend(found)

    if page < 5:
        time.sleep(1)

# Strip [Foil] suffix and deduplicate while preserving order
seen = set()
clean = []
for name in names:
    base = name.replace(" [Foil]", "").strip()
    if base not in seen:
        seen.add(base)
        clean.append(base)

print(f"\nTotal unique cards: {len(clean)}")
for name in clean:
    print(name)
