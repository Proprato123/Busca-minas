# generate_contributions.py
# Usage: python generate_contributions.py <github_username>
# Example: python generate_contributions.py EmmanuelPerezVivas

import sys
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: python generate_contributions.py <github_username>")
    sys.exit(1)

username = sys.argv[1]
url = f"https://github.com/users/{username}/contributions"
resp = requests.get(url)
if resp.status_code != 200:
    print("Failed to fetch contributions SVG. Status:", resp.status_code)
    sys.exit(1)

soup = BeautifulSoup(resp.text, "html.parser")
rects = soup.find_all("rect", {"data-date": True})

# We will store a list of weeks; each week is list of days {date, count, x, y}
# But simpler: create a grid by date -> {date, count, week_index, day_index}
entries = []
for rect in rects:
    date = rect.get("data-date")
    count = rect.get("data-count", "0")
    # position attributes may be present (data-x / data-y), fallback to x/y
    x = rect.get("x")
    y = rect.get("y")
    # normalize types
    try:
        count = int(count)
    except:
        count = 0
    entries.append({
        "date": date,
        "count": count,
        "x": int(x) if x is not None else None,
        "y": int(y) if y is not None else None
    })

# Sort entries by date (old -> new)
entries.sort(key=lambda e: e["date"])

# Optionally derive a 2D grid by weeks (columns). Determine week index by detecting changes in x
# Simpler: group by week by integer division: contributions SVG is weekly columns (approx 53)
# We'll compute week index from order: group every 7 days into weeks, but note the first week may be partial.
# Safer: compute weeks by scanning unique x positions (if x available)
weeks = {}
if entries and entries[0]["x"] is not None:
    # group by x coordinate
    for e in entries:
        key = e["x"]
        if key not in weeks:
            weeks[key] = []
        weeks[key].append(e)
    # order by x
    sorted_weeks = [weeks[k] for k in sorted(weeks.keys())]
else:
    # fallback: chunk by 7
    sorted_weeks = [entries[i:i+7] for i in range(0, len(entries), 7)]

# create a simplified structure: weeks -> days (date, count)
grid = []
for w in sorted_weeks:
    col = []
    for d in w:
        col.append({"date": d["date"], "count": d["count"]})
    grid.append(col)

output = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "username": username,
    "weeks": grid  # array of columns; each column is up to 7 day objects
}

out_filename = "contributions.json"
with open(out_filename, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Wrote {out_filename} with {len(grid)} weeks.")
