"""
Export clinical trials data from SQLite to Excel.
Sheets: All Trials, Summary by Company, Summary by Phase, Summary by Country
"""
import sqlite3
import pandas as pd
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DB_PATH = "trials.db"
OUTPUT_PATH = "clinical_trials_data.xlsx"

BRAND_BLUE = "1a1a2e"
ACCENT_BLUE = "0093D0"
LIGHT_BLUE = "D6EAF8"
LIGHT_GRAY = "F2F3F4"


def style_header_row(ws, row=1, fill_color=BRAND_BLUE, font_color="FFFFFF"):
    fill = PatternFill(fill_type="solid", fgColor=fill_color)
    font = Font(bold=True, color=font_color, size=11)
    for cell in ws[row]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def style_data_rows(ws, start_row=2):
    thin = Side(style="thin", color="CCCCCC")
    border = Border(bottom=thin, right=thin)
    for i, row in enumerate(ws.iter_rows(min_row=start_row), start=start_row):
        fill_color = LIGHT_BLUE if i % 2 == 0 else "FFFFFF"
        fill = PatternFill(fill_type="solid", fgColor=fill_color)
        for cell in row:
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")


def auto_fit_columns(ws, min_width=10, max_width=40):
    for col in ws.columns:
        max_len = max((len(str(c.value)) if c.value else 0) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, min_width), max_width)


def freeze_and_filter(ws):
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


conn = sqlite3.connect(DB_PATH)

FOCUS_COUNTRIES = ('Israel','Belgium','Switzerland','Austria','Sweden','Denmark','Norway','Ireland')
COUNTRY_IN = ",".join(f"'{c}'" for c in FOCUS_COUNTRIES)

# --- Sheet 1: All Trials ---
df_trials = pd.read_sql_query(f"""
    SELECT
        t.nct_id                                    AS "NCT ID",
        t.company                                   AS "Company",
        t.sponsor                                   AS "Sponsor (ClinicalTrials.gov)",
        REPLACE(t.phase, 'PHASE', 'Phase ')         AS "Phase",
        t.start_year                                AS "Start Year",
        t.start_month                               AS "Start Month",
        GROUP_CONCAT(tc.country || ' (' || COALESCE(tc.site_count,1) || ')', ', ')
                                                    AS "Countries (sites per country)"
    FROM trials t
    LEFT JOIN trial_countries tc ON t.nct_id = tc.nct_id
    GROUP BY t.nct_id
    ORDER BY t.start_year DESC, t.start_month DESC
""", conn)

# --- Sheet 2: Summary by Company & Year ---
df_company_year = pd.read_sql_query(f"""
    SELECT
        t.company                                   AS "Company",
        t.start_year                                AS "Year",
        REPLACE(t.phase, 'PHASE', 'Phase ')         AS "Phase",
        COUNT(DISTINCT t.nct_id)                    AS "Number of Trials",
        CAST(SUM(COALESCE(tc.site_count, 1)) AS INTEGER)
                                                    AS "Total Research Sites"
    FROM trials t
    JOIN trial_countries tc ON t.nct_id = tc.nct_id
    WHERE tc.country IN ({COUNTRY_IN})
    GROUP BY t.company, t.start_year, t.phase
    ORDER BY t.company, t.start_year, t.phase
""", conn)

# --- Sheet 3: Summary by Company (pivot — trial counts) ---
df_pivot_raw = pd.read_sql_query("""
    SELECT company, start_year, COUNT(*) AS cnt
    FROM trials
    GROUP BY company, start_year
    ORDER BY company, start_year
""", conn)
df_pivot = df_pivot_raw.pivot(index="company", columns="start_year", values="cnt").fillna(0).astype(int)
df_pivot["Total"] = df_pivot.sum(axis=1)
df_pivot = df_pivot.sort_values("Total", ascending=False).reset_index()
df_pivot.columns.name = None
df_pivot = df_pivot.rename(columns={"company": "Company"})

# --- Sheet 4: Summary by Country ---
df_country = pd.read_sql_query(f"""
    SELECT
        tc.country                                          AS "Country",
        t.company                                          AS "Company",
        REPLACE(t.phase, 'PHASE', 'Phase ')                AS "Phase",
        COUNT(DISTINCT t.nct_id)                           AS "Number of Trials",
        CAST(SUM(COALESCE(tc.site_count, 1)) AS INTEGER)   AS "Total Research Sites"
    FROM trial_countries tc
    JOIN trials t ON tc.nct_id = t.nct_id
    WHERE tc.country IN ({COUNTRY_IN})
    GROUP BY tc.country, t.company, t.phase
    ORDER BY tc.country, t.company, t.phase
""", conn)

# --- Sheet 5: Country Pivot (trial counts) ---
df_country_pivot_raw = pd.read_sql_query(f"""
    SELECT tc.country AS "Country", t.company AS "Company", COUNT(DISTINCT t.nct_id) AS cnt
    FROM trial_countries tc
    JOIN trials t ON tc.nct_id = t.nct_id
    WHERE tc.country IN ({COUNTRY_IN})
    GROUP BY tc.country, t.company
""", conn)
df_country_pivot = df_country_pivot_raw.pivot(index="Country", columns="Company", values="cnt").fillna(0).astype(int)
df_country_pivot["Total Trials"] = df_country_pivot.sum(axis=1)
df_country_pivot = df_country_pivot.sort_values("Total Trials", ascending=False).reset_index()
df_country_pivot.columns.name = None

# --- Sheet 6: Country Pivot (research sites) ---
df_sites_pivot_raw = pd.read_sql_query(f"""
    SELECT
        tc.country                                          AS "Country",
        t.company                                          AS "Company",
        CAST(SUM(COALESCE(tc.site_count, 1)) AS INTEGER)   AS sites
    FROM trial_countries tc
    JOIN trials t ON tc.nct_id = t.nct_id
    WHERE tc.country IN ({COUNTRY_IN})
    GROUP BY tc.country, t.company
""", conn)
df_sites_pivot = df_sites_pivot_raw.pivot(index="Country", columns="Company", values="sites").fillna(0).astype(int)
df_sites_pivot["Total Sites"] = df_sites_pivot.sum(axis=1)
df_sites_pivot = df_sites_pivot.sort_values("Total Sites", ascending=False).reset_index()
df_sites_pivot.columns.name = None

conn.close()

# --- Write to Excel ---
with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
    sheets = [
        (df_trials,          "All Trials"),
        (df_company_year,    "By Company & Year"),
        (df_pivot,           "Company Pivot (trials)"),
        (df_country,         "By Country"),
        (df_country_pivot,   "Country Pivot (trials)"),
        (df_sites_pivot,     "Country Pivot (sites)"),
    ]

    for df, sheet_name in sheets:
        df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
        ws = writer.sheets[sheet_name]
        style_header_row(ws)
        style_data_rows(ws)
        auto_fit_columns(ws)
        freeze_and_filter(ws)
        ws.row_dimensions[1].height = 30

print(f"Excel file saved: {OUTPUT_PATH}")
for df, name in sheets:
    print(f"  {name}: {len(df)} rows")
