"""
Clinical trials dashboard — top 10 pharma, 8 countries (Israel + 7 European), 2015-2025.
Interactive company filter: click to select/deselect, multi-select, All button.
"""
import sqlite3
import json
import pandas as pd

DB_PATH  = "trials.db"
OUT_PATH = "pharma_trials_dashboard.html"
MIN_YEAR = 2015
MAX_YEAR = 2025

COMPANIES = [
    "Pfizer", "Johnson & Johnson", "Roche", "Novartis", "Merck",
    "AbbVie", "Bristol-Myers Squibb", "AstraZeneca", "Sanofi", "Eli Lilly",
]

COUNTRIES = [
    "Israel",
    "Belgium", "Switzerland", "Austria", "Sweden",
    "Denmark", "Norway", "Ireland",
]

COUNTRY_COLORS = {
    "Israel":      "#0038B8",
    "Belgium":     "#E63946",
    "Switzerland": "#2A9D8F",
    "Austria":     "#E9C46A",
    "Sweden":      "#264653",
    "Denmark":     "#F4A261",
    "Norway":      "#457B9D",
    "Ireland":     "#6A994E",
}

PHASES = ["PHASE1", "PHASE2", "PHASE3"]
YEARS  = list(range(MIN_YEAR, MAX_YEAR + 1))


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_trials = pd.read_sql(
        "SELECT nct_id, company, phase, start_year, enrollment FROM trials "
        "WHERE start_year BETWEEN ? AND ? AND phase IN ('PHASE1','PHASE2','PHASE3')",
        conn, params=(MIN_YEAR, MAX_YEAR),
    )
    placeholders = ",".join("?" * len(COUNTRIES))
    df_countries = pd.read_sql(
        f"SELECT nct_id, country FROM trial_countries WHERE country IN ({placeholders})",
        conn, params=COUNTRIES,
    )
    conn.close()
    return df_trials.merge(df_countries, on="nct_id", how="inner")


def build_company_data(df):
    """
    Returns two nested dicts:
      trial_data[company][phase][country][year]  = unique trial count
      enroll_data[company][phase][country][year] = sum of enrollment
    """
    empty = lambda: {co: {ph: {ct: {yr: 0 for yr in YEARS}
                               for ct in COUNTRIES}
                          for ph in PHASES}
                    for co in COMPANIES}

    trial_data  = empty()
    enroll_data = empty()

    trial_agg = (
        df.groupby(["company", "phase", "country", "start_year"])["nct_id"]
        .nunique()
        .reset_index(name="cnt")
    )
    enroll_agg = (
        df.drop_duplicates(subset=["nct_id", "country"])
        .dropna(subset=["enrollment"])
        .groupby(["company", "phase", "country", "start_year"])["enrollment"]
        .sum()
        .reset_index(name="enr")
    )

    for row in trial_agg.itertuples(index=False):
        co, ph, ct, yr, cnt = row.company, row.phase, row.country, row.start_year, row.cnt
        if co in trial_data and ph in trial_data[co] and ct in trial_data[co][ph] and yr in trial_data[co][ph][ct]:
            trial_data[co][ph][ct][yr] = int(cnt)

    for row in enroll_agg.itertuples(index=False):
        co, ph, ct, yr, enr = row.company, row.phase, row.country, row.start_year, row.enr
        if co in enroll_data and ph in enroll_data[co] and ct in enroll_data[co][ph] and yr in enroll_data[co][ph][ct]:
            enroll_data[co][ph][ct][yr] = int(enr)

    return trial_data, enroll_data


def build_dashboard():
    print("Loading data...")
    df = load_data()
    print(f"  {df['nct_id'].nunique()} unique trials loaded")

    print("Building per-company data matrices...")
    trial_data, enroll_data = build_company_data(df)

    # ── Chart configurations (order = display order) ──────────────────────
    SECTION_A = "Section A — Number of Trials Started"
    SECTION_B = "Section B — Participants Enrolled"

    chart_configs = []
    for ph in PHASES:
        label = ph.replace("PHASE", "Phase ")
        chart_configs.append({
            "id":      f"chart_{ph.lower()}_trials",
            "section": SECTION_A,
            "label":   label,
            "type":    "trials",
            "phases":  [ph],
            "title":   f"<b>{label}</b> — Trials Started per Year",
            "ylabel":  "Number of Trials",
            "height":  520,
        })
    chart_configs.append({
        "id":      "chart_all_trials",
        "section": SECTION_A,
        "label":   "All Phases — Combined",
        "type":    "trials",
        "phases":  PHASES,
        "title":   "<b>All Phases Combined</b> — Total Trials Started per Year (Ph.1+Ph.2+Ph.3)",
        "ylabel":  "Number of Trials",
        "height":  520,
    })
    for ph in PHASES:
        label = ph.replace("PHASE", "Phase ")
        chart_configs.append({
            "id":      f"chart_{ph.lower()}_enroll",
            "section": SECTION_B,
            "label":   label,
            "type":    "enrollment",
            "phases":  [ph],
            "title":   f"<b>{label}</b> — Participants Enrolled per Year",
            "ylabel":  "Participants",
            "height":  520,
        })
    chart_configs.append({
        "id":      "chart_all_enroll",
        "section": SECTION_B,
        "label":   "All Phases — Combined",
        "type":    "enrollment",
        "phases":  PHASES,
        "title":   "<b>All Phases Combined</b> — Total Participants Enrolled per Year (Ph.1+Ph.2+Ph.3)",
        "ylabel":  "Participants",
        "height":  560,
    })

    # ── Build HTML chart blocks ────────────────────────────────────────────
    header_style = (
        "font-size:26px;font-weight:bold;color:#fff;"
        "background:linear-gradient(135deg,#1a1a2e,#0093D0);"
        "padding:14px 20px;border-radius:8px;margin:30px 0 5px 0;font-family:Arial"
    )
    sub_style = (
        "font-size:22px;font-weight:bold;color:#1a1a2e;"
        "border-left:5px solid #0093D0;padding-left:12px;"
        "margin:40px 0 10px 0;font-family:Arial"
    )
    card_style = (
        "background:white;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.12);margin-bottom:25px;padding:15px"
    )

    body_blocks = []
    current_section = None
    for cfg in chart_configs:
        if cfg["section"] != current_section:
            current_section = cfg["section"]
            body_blocks.append(f'<div style="{header_style}">{current_section}</div>')
            if current_section == SECTION_B:
                body_blocks.append(
                    '<p style="font-family:Arial;color:#555;font-size:13px;margin:0 0 20px 4px">'
                    "Each trial’s total enrollment is attributed to its start year. "
                    "Trials without enrollment data are excluded. "
                    "Note: enrollment is per-trial globally — all countries in the trial share the same number.</p>"
                )
        body_blocks.append(f'<div style="{sub_style}">{cfg["label"]}</div>')
        body_blocks.append(f'<div style="{card_style}"><div id="{cfg["id"]}"></div></div>')

    company_buttons = '<button id="btn-all" class="co-btn active">All</button>\n    ' + "\n    ".join(
        f'<button class="co-btn active" data-co="{co}">{co}</button>'
        for co in COMPANIES
    )

    # ── JavaScript ────────────────────────────────────────────────────────
    js = f"""
const TRIAL_DATA   = {json.dumps(trial_data)};
const ENROLL_DATA  = {json.dumps(enroll_data)};
const COMPANIES    = {json.dumps(COMPANIES)};
const COUNTRIES    = {json.dumps(COUNTRIES)};
const COLORS       = {json.dumps(COUNTRY_COLORS)};
const YEARS        = {json.dumps(YEARS)};
const CHART_CFGS   = {json.dumps(chart_configs)};

let selected = new Set(COMPANIES);

function aggregate(dataObj, companies, phases) {{
  const result = {{}};
  for (const ct of COUNTRIES) {{
    result[ct] = YEARS.map(yr => {{
      let s = 0;
      for (const co of companies)
        for (const ph of phases)
          s += (dataObj[co]?.[ph]?.[ct]?.[yr]) || 0;
      return s;
    }});
  }}
  return result;
}}

function traces(agg) {{
  return COUNTRIES.map(ct => ({{
    x: YEARS, y: agg[ct], name: ct,
    mode: 'lines+markers',
    line: {{color: COLORS[ct], width: 2.5}},
    marker: {{size: 7}},
    type: 'scatter',
    hovertemplate: '<b>' + ct + '</b><br>Year: %{{x}}<br>Value: %{{y:,}}<extra></extra>',
  }}));
}}

function layout(title, ylabel, height) {{
  return {{
    title: {{text: title, font: {{size: 19}}}},
    xaxis: {{title:'Year', tickmode:'array', tickvals:YEARS, ticktext:YEARS.map(String), tickangle:-45}},
    yaxis: {{title: ylabel}},
    legend: {{title:{{text:'Country'}}, x:1.01, y:1, font:{{size:12}}}},
    hovermode: 'x unified',
    template: 'plotly_white',
    height: height,
    margin: {{r:180, t:70, b:80}},
  }};
}}

function redrawAll() {{
  const sel = Array.from(selected);
  for (const cfg of CHART_CFGS) {{
    const src = cfg.type === 'trials' ? TRIAL_DATA : ENROLL_DATA;
    Plotly.react(cfg.id, traces(aggregate(src, sel, cfg.phases)),
                 layout(cfg.title, cfg.ylabel, cfg.height));
  }}
}}

function syncButtons() {{
  const all = selected.size === COMPANIES.length;
  document.getElementById('btn-all').classList.toggle('active', all);
  document.querySelectorAll('.co-btn[data-co]').forEach(b => {{
    b.classList.toggle('active', selected.has(b.dataset.co));
  }});
}}

document.getElementById('btn-all').addEventListener('click', () => {{
  COMPANIES.forEach(c => selected.add(c));
  syncButtons(); redrawAll();
}});

document.querySelectorAll('.co-btn[data-co]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const co = btn.dataset.co;
    if (selected.has(co)) {{
      if (selected.size > 1) selected.delete(co);
    }} else {{
      selected.add(co);
    }}
    syncButtons(); redrawAll();
  }});
}});

// Init
for (const cfg of CHART_CFGS) {{
  const src = cfg.type === 'trials' ? TRIAL_DATA : ENROLL_DATA;
  Plotly.newPlot(cfg.id, traces(aggregate(src, COMPANIES, cfg.phases)),
                 layout(cfg.title, cfg.ylabel, cfg.height), {{responsive:true}});
}}
"""

    # ── Final HTML ────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pharma Clinical Trials — European Countries + Israel</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body   {{ font-family:Arial,sans-serif; background:#f5f7fa; margin:0; padding:20px 30px; }}
    h1     {{ text-align:center; color:#1a1a2e; margin-bottom:4px; font-size:26px; }}
    .sub   {{ text-align:center; color:#666; margin-bottom:16px; font-size:14px; }}

    #filter-bar {{
      display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:center;
      background:#fff; border:1px solid #dce2ea; border-radius:10px;
      padding:12px 20px; margin:0 0 22px 0;
    }}
    .filter-label {{
      font-size:13px; font-weight:700; color:#1a1a2e; margin-right:4px; white-space:nowrap;
    }}
    .co-btn {{
      padding:6px 15px; border-radius:20px; border:2px solid #c8d0db;
      background:#fff; color:#555; font-size:13px; font-weight:600;
      cursor:pointer; transition:background 0.15s, color 0.15s, border-color 0.15s;
      white-space:nowrap;
    }}
    .co-btn:hover  {{ border-color:#0093D0; color:#0093D0; }}
    .co-btn.active {{ background:#1a1a2e; color:#fff; border-color:#1a1a2e; }}
    #btn-all       {{ border-color:#0093D0; color:#0093D0; }}
    #btn-all.active {{ background:#0093D0; color:#fff; border-color:#0093D0; }}
  </style>
</head>
<body>
  <h1>Top 10 Pharma — Clinical Trials Dashboard</h1>
  <p class="sub">
    Israel &middot; Belgium &middot; Switzerland &middot; Austria &middot;
    Sweden &middot; Denmark &middot; Norway &middot; Ireland
    &nbsp;|&nbsp; 2015&ndash;2025 &nbsp;|&nbsp; Click legend to toggle countries
    &nbsp;|&nbsp; Data source:&nbsp;<a href="https://clinicaltrials.gov" target="_blank"
      style="color:#0093D0;text-decoration:none;font-weight:bold;">ClinicalTrials.gov</a>
  </p>

  <div id="filter-bar">
    <span class="filter-label">Filter by Company:</span>
    {company_buttons}
  </div>

  {''.join(body_blocks)}

  <script>{js}</script>
</body>
</html>"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    kb = len(html) // 1024
    print(f"\nSaved: {OUT_PATH}  ({kb} KB)")


if __name__ == "__main__":
    build_dashboard()
