"""
Download clinical trials data from ClinicalTrials.gov API v2
Top 10 pharma companies, Phase 1/2/3, last 10 years (2015-2025)
Stores results in SQLite database.
"""
import sqlite3
import json
import time
import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError
from datetime import datetime

DB_PATH = "trials.db"
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000

# Top 10 pharma companies by global revenue (2023-2024)
# Using search terms that match their ClinicalTrials.gov sponsor names
TOP_PHARMA = {
    "Pfizer":              ["Pfizer"],
    "Johnson & Johnson":   ["Janssen", "Johnson & Johnson"],
    "Roche":               ["Hoffmann-La Roche", "Genentech"],
    "Novartis":            ["Novartis"],
    "Merck":               ["Merck Sharp", "Merck &", "MSD "],
    "AbbVie":              ["AbbVie"],
    "Bristol-Myers Squibb":["Bristol-Myers Squibb"],
    "AstraZeneca":         ["AstraZeneca"],
    "Sanofi":              ["Sanofi"],
    "Eli Lilly":           ["Eli Lilly"],
}

PHASES = ["PHASE1", "PHASE2", "PHASE3"]
FIELDS = "NCTId,StartDate,Phase,LeadSponsorName,LocationCountry"
MIN_YEAR = 2015


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trials (
            nct_id      TEXT PRIMARY KEY,
            company     TEXT,
            sponsor     TEXT,
            phase       TEXT,
            start_year  INTEGER,
            start_month INTEGER
        );
        CREATE TABLE IF NOT EXISTS trial_countries (
            nct_id   TEXT,
            country  TEXT,
            PRIMARY KEY (nct_id, country)
        );
        CREATE TABLE IF NOT EXISTS download_progress (
            company     TEXT,
            sponsor     TEXT,
            next_token  TEXT,
            done        INTEGER DEFAULT 0,
            PRIMARY KEY (company, sponsor)
        );
    """)
    conn.commit()


def fetch_page(sponsor_query, next_token=None):
    params = {
        "format": "json",
        "pageSize": PAGE_SIZE,
        "fields": FIELDS,
        "query.spons": sponsor_query,
    }
    if next_token:
        params["pageToken"] = next_token

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
    raise RuntimeError(f"Failed to fetch: {url}")


def parse_year_month(date_str):
    """Parse '2021-03' or '2021-03-15' → (2021, 3)"""
    if not date_str:
        return None, None
    parts = date_str.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else None
        return year, month
    except (ValueError, IndexError):
        return None, None


def download_sponsor(conn, company_name, sponsor_term):
    """Download all Phase1/2/3 trials for a sponsor term."""
    cursor = conn.cursor()

    # Check if already done
    cursor.execute(
        "SELECT done, next_token FROM download_progress WHERE company=? AND sponsor=?",
        (company_name, sponsor_term)
    )
    row = cursor.fetchone()
    if row and row[0] == 1:
        print(f"  [{sponsor_term}] Already complete, skipping.")
        return
    next_token = row[1] if row else None

    page_num = 0
    total_saved = 0

    while True:
        page_num += 1
        print(f"  [{sponsor_term}] Page {page_num}...", end=" ", flush=True)

        data = fetch_page(sponsor_term, next_token)
        studies = data.get("studies", [])
        next_token = data.get("nextPageToken")

        inserted = 0
        for study in studies:
            proto = study.get("protocolSection", {})

            # NCT ID
            nct_id = proto.get("identificationModule", {}).get("nctId")
            if not nct_id:
                continue

            # Phase filter
            phases = proto.get("designModule", {}).get("phases", [])
            phase = None
            for p in PHASES:
                if p in phases:
                    phase = p
                    break
            if not phase:
                continue

            # Start date filter
            start_date = proto.get("statusModule", {}).get("startDateStruct", {}).get("date")
            year, month = parse_year_month(start_date)
            if not year or year < MIN_YEAR:
                continue

            # Sponsor
            sponsor = proto.get("sponsorCollaboratorsModule", {}).get(
                "leadSponsor", {}).get("name", "")

            # Countries
            locations = proto.get("contactsLocationsModule", {}).get("locations", [])
            countries = list({loc["country"] for loc in locations if loc.get("country")})

            # Insert trial
            cursor.execute(
                "INSERT OR IGNORE INTO trials VALUES (?,?,?,?,?,?)",
                (nct_id, company_name, sponsor, phase, year, month)
            )
            # Insert countries
            for country in countries:
                cursor.execute(
                    "INSERT OR IGNORE INTO trial_countries VALUES (?,?)",
                    (nct_id, country)
                )
            inserted += 1

        conn.commit()
        total_saved += inserted
        print(f"saved {inserted} -> total {total_saved}")

        # Save progress
        cursor.execute(
            "INSERT OR REPLACE INTO download_progress VALUES (?,?,?,?)",
            (company_name, sponsor_term, next_token, 0)
        )
        conn.commit()

        if not next_token:
            break
        time.sleep(0.2)  # polite rate limiting

    # Mark as done
    cursor.execute(
        "INSERT OR REPLACE INTO download_progress VALUES (?,?,?,?)",
        (company_name, sponsor_term, None, 1)
    )
    conn.commit()
    print(f"  [{sponsor_term}] Done. Total saved: {total_saved}")


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    print(f"Starting download — {len(TOP_PHARMA)} companies, phases 1/2/3, years {MIN_YEAR}+")
    print(f"Database: {DB_PATH}\n")

    for company, sponsors in TOP_PHARMA.items():
        print(f"\n=== {company} ===")
        for sponsor_term in sponsors:
            download_sponsor(conn, company, sponsor_term)

    # Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trials")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT company, COUNT(*) FROM trials GROUP BY company ORDER BY COUNT(*) DESC")
    rows = cursor.fetchall()

    print(f"\n{'='*50}")
    print(f"DOWNLOAD COMPLETE — {total} trials total")
    print(f"{'='*50}")
    for company, count in rows:
        print(f"  {company:<25} {count:>5} trials")

    conn.close()


if __name__ == "__main__":
    main()
