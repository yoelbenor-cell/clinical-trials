"""
Enrich trial_countries with site_count:
number of research sites (locations) per country per trial.
"""
import sqlite3
import json
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from collections import Counter

DB_PATH  = "trials.db"
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
BATCH    = 50


def add_column(conn):
    try:
        conn.execute("ALTER TABLE trial_countries ADD COLUMN site_count INTEGER")
        conn.commit()
        print("Added 'site_count' column to trial_countries.")
    except Exception:
        print("'site_count' column already exists, continuing.")


def fetch_batch(nct_ids):
    params = {
        "format":   "json",
        "pageSize": len(nct_ids),
        "fields":   "NCTId,LocationFacility,LocationCountry",
        "query.id": " OR ".join(nct_ids),
    }
    url = BASE_URL + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ClinicalTrialsResearch/1.0"})
    for attempt in range(5):
        try:
            with urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except Exception as e:
            time.sleep(2 ** attempt)
            print(f"  Retry {attempt+1}: {e}")
    raise RuntimeError(f"Failed: {url}")


def main():
    conn = sqlite3.connect(DB_PATH)
    add_column(conn)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT nct_id FROM trial_countries WHERE site_count IS NULL")
    all_ids = [r[0] for r in cur.fetchall()]
    total   = len(all_ids)
    print(f"Fetching site counts for {total} trials (batch={BATCH})...\n")

    updated = 0
    for i in range(0, total, BATCH):
        batch = all_ids[i:i + BATCH]
        pct   = i / total * 100
        print(f"  [{i+1}-{min(i+BATCH,total)}/{total}  {pct:.0f}%]...", end=" ", flush=True)

        data    = fetch_batch(batch)
        studies = data.get("studies", [])
        count   = 0

        for study in studies:
            proto  = study.get("protocolSection", {})
            nct_id = proto.get("identificationModule", {}).get("nctId")
            if not nct_id:
                continue
            locs   = proto.get("contactsLocationsModule", {}).get("locations", [])
            counts = Counter(loc["country"] for loc in locs if loc.get("country"))
            for country, n in counts.items():
                cur.execute(
                    "UPDATE trial_countries SET site_count=? WHERE nct_id=? AND country=?",
                    (n, nct_id, country)
                )
            count += 1

        conn.commit()
        updated += count
        print(f"updated {count}")
        time.sleep(0.2)

    cur.execute("SELECT COUNT(*), AVG(site_count), MAX(site_count) FROM trial_countries WHERE site_count IS NOT NULL")
    have, avg, mx = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM trial_countries WHERE site_count IS NULL")
    null = cur.fetchone()[0]

    print(f"\nDONE — rows with site_count: {have}/{have+null}")
    print(f"Avg sites/country/trial: {avg:.1f}  |  Max: {mx}")
    conn.close()


if __name__ == "__main__":
    main()
