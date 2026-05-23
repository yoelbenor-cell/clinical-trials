"""
Enrich existing trials with EnrollmentCount from ClinicalTrials.gov API v2.
Reads NCT IDs from DB, fetches enrollment in batches, updates trials table.
"""
import sqlite3
import json
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode

DB_PATH  = "trials.db"
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
BATCH    = 100   # NCT IDs per request (comma-separated in query.id)


def add_enrollment_column(conn):
    try:
        conn.execute("ALTER TABLE trials ADD COLUMN enrollment INTEGER")
        conn.commit()
        print("Added 'enrollment' column to trials table.")
    except Exception:
        print("'enrollment' column already exists, continuing.")


def fetch_enrollment_batch(nct_ids):
    """Fetch enrollment counts for a list of NCT IDs."""
    id_query = " OR ".join(nct_ids)
    params = {
        "format":    "json",
        "pageSize":  len(nct_ids),
        "fields":    "NCTId,EnrollmentCount",
        "query.id":  id_query,
    }
    url = BASE_URL + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ClinicalTrialsResearch/1.0"})
    for attempt in range(5):
        try:
            with urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except Exception as e:
            wait = 2 ** attempt
            print(f"  Retry {attempt+1}/5 after {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"Failed: {url}")


def main():
    conn = sqlite3.connect(DB_PATH)
    add_enrollment_column(conn)

    cur = conn.cursor()
    cur.execute("SELECT nct_id FROM trials WHERE enrollment IS NULL")
    all_ids = [row[0] for row in cur.fetchall()]
    total   = len(all_ids)
    print(f"Fetching enrollment for {total} trials in batches of {BATCH}...\n")

    updated  = 0
    missing  = 0
    batch_n  = 0

    for i in range(0, total, BATCH):
        batch     = all_ids[i:i + BATCH]
        batch_n  += 1
        pct       = (i / total) * 100
        print(f"  Batch {batch_n} ({i+1}-{min(i+BATCH, total)} of {total}, {pct:.0f}%)...",
              end=" ", flush=True)

        data    = fetch_enrollment_batch(batch)
        studies = data.get("studies", [])

        count = 0
        for study in studies:
            proto    = study.get("protocolSection", {})
            nct_id   = proto.get("identificationModule", {}).get("nctId")
            enroll   = proto.get("designModule", {}).get("enrollmentInfo", {}).get("count")
            if nct_id and enroll is not None:
                cur.execute(
                    "UPDATE trials SET enrollment=? WHERE nct_id=?",
                    (int(enroll), nct_id)
                )
                count += 1

        conn.commit()
        updated += count
        missing += len(batch) - count
        print(f"updated {count}")
        time.sleep(0.15)

    # Summary
    cur.execute("SELECT COUNT(*) FROM trials WHERE enrollment IS NOT NULL")
    have = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM trials WHERE enrollment IS NULL")
    null = cur.fetchone()[0]
    cur.execute("SELECT AVG(enrollment), MAX(enrollment) FROM trials WHERE enrollment IS NOT NULL")
    avg, mx = cur.fetchone()

    print(f"\n{'='*50}")
    print(f"DONE — {updated} updated, {missing} still missing")
    print(f"Trials with enrollment: {have} / {have+null}")
    print(f"Avg enrollment: {avg:.0f} | Max: {mx}")
    print(f"{'='*50}")
    conn.close()


if __name__ == "__main__":
    main()
