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

# Population in millions — World Bank WDI (2024-2025: estimates)
POPULATION = {
    "Israel":      {2015:8.38,  2016:8.54,  2017:8.71,  2018:8.88,  2019:9.05,  2020:9.22,  2021:9.45,  2022:9.66,  2023:9.84,  2024:10.01, 2025:10.20},
    "Belgium":     {2015:11.24, 2016:11.31, 2017:11.35, 2018:11.43, 2019:11.51, 2020:11.59, 2021:11.59, 2022:11.66, 2023:11.74, 2024:11.87, 2025:11.95},
    "Switzerland": {2015:8.33,  2016:8.40,  2017:8.48,  2018:8.55,  2019:8.60,  2020:8.67,  2021:8.74,  2022:8.82,  2023:8.96,  2024:9.10,  2025:9.18},
    "Austria":     {2015:8.66,  2016:8.74,  2017:8.80,  2018:8.85,  2019:8.90,  2020:8.93,  2021:9.04,  2022:9.10,  2023:9.10,  2024:9.15,  2025:9.21},
    "Sweden":      {2015:9.80,  2016:9.92,  2017:10.07, 2018:10.18, 2019:10.29, 2020:10.33, 2021:10.42, 2022:10.52, 2023:10.55, 2024:10.65, 2025:10.75},
    "Denmark":     {2015:5.69,  2016:5.73,  2017:5.75,  2018:5.80,  2019:5.81,  2020:5.82,  2021:5.84,  2022:5.88,  2023:5.96,  2024:6.03,  2025:6.10},
    "Norway":      {2015:5.19,  2016:5.23,  2017:5.27,  2018:5.30,  2019:5.33,  2020:5.37,  2021:5.41,  2022:5.43,  2023:5.52,  2024:5.59,  2025:5.67},
    "Ireland":     {2015:4.63,  2016:4.71,  2017:4.78,  2018:4.86,  2019:4.94,  2020:5.00,  2021:5.13,  2022:5.24,  2023:5.31,  2024:5.41,  2025:5.51},
}

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
        "SELECT nct_id, company, phase, start_year FROM trials "
        "WHERE start_year BETWEEN ? AND ? AND phase IN ('PHASE1','PHASE2','PHASE3')",
        conn, params=(MIN_YEAR, MAX_YEAR),
    )
    placeholders = ",".join("?" * len(COUNTRIES))
    df_countries = pd.read_sql(
        f"SELECT nct_id, country, COALESCE(site_count, 1) AS site_count "
        f"FROM trial_countries WHERE country IN ({placeholders})",
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

    trial_data = empty()
    sites_data = empty()

    trial_agg = (
        df.groupby(["company", "phase", "country", "start_year"])["nct_id"]
        .nunique()
        .reset_index(name="cnt")
    )
    sites_agg = (
        df.groupby(["company", "phase", "country", "start_year"])["site_count"]
        .sum()
        .reset_index(name="sites")
    )

    for row in trial_agg.itertuples(index=False):
        co, ph, ct, yr, cnt = row.company, row.phase, row.country, row.start_year, row.cnt
        if co in trial_data and ph in trial_data[co] and ct in trial_data[co][ph] and yr in trial_data[co][ph][ct]:
            trial_data[co][ph][ct][yr] = int(cnt)

    for row in sites_agg.itertuples(index=False):
        co, ph, ct, yr, sites = row.company, row.phase, row.country, row.start_year, row.sites
        if co in sites_data and ph in sites_data[co] and ct in sites_data[co][ph] and yr in sites_data[co][ph][ct]:
            sites_data[co][ph][ct][yr] = int(sites)

    return trial_data, sites_data


def build_dashboard():
    print("Loading data...")
    df = load_data()
    print(f"  {df['nct_id'].nunique()} unique trials loaded")

    print("Building per-company data matrices...")
    trial_data, sites_data = build_company_data(df)

    # ── Chart configurations (order = display order) ──────────────────────
    SECTION_A = "Section A — Number of Trials Started"
    SECTION_B = "Section B — Research Sites per Country"

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
            "id":      f"chart_{ph.lower()}_sites",
            "section": SECTION_B,
            "label":   label,
            "type":    "sites",
            "phases":  [ph],
            "title":   f"<b>{label}</b> — Research Sites per Year",
            "ylabel":  "Research Sites",
            "height":  520,
        })
    chart_configs.append({
        "id":      "chart_all_sites",
        "section": SECTION_B,
        "label":   "All Phases — Combined",
        "type":    "sites",
        "phases":  PHASES,
        "title":   "<b>All Phases Combined</b> — Total Research Sites per Year (Ph.1+Ph.2+Ph.3)",
        "ylabel":  "Research Sites",
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
                    'Number of active research sites (locations) per country per year, summed across selected companies. '
                    'Source: ClinicalTrials.gov location data.</p>'
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
const SITES_DATA   = {json.dumps(sites_data)};
const COMPANIES    = {json.dumps(COMPANIES)};
const COUNTRIES    = {json.dumps(COUNTRIES)};
const COLORS       = {json.dumps(COUNTRY_COLORS)};
const YEARS        = {json.dumps(YEARS)};
const CHART_CFGS   = {json.dumps(chart_configs)};
const POPULATION   = {json.dumps(POPULATION)};

let selected   = new Set(COMPANIES);
let perCapita  = false;

function aggregate(dataObj, companies, phases) {{
  const result = {{}};
  for (const ct of COUNTRIES) {{
    result[ct] = YEARS.map(yr => {{
      let s = 0;
      for (const co of companies)
        for (const ph of phases)
          s += (dataObj[co]?.[ph]?.[ct]?.[yr]) || 0;
      if (perCapita) {{
        const pop = POPULATION[ct]?.[yr];
        return pop ? +((s / pop).toFixed(3)) : 0;
      }}
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

function yLabel(base) {{
  return perCapita ? base + ' per Million Population' : base;
}}

function redrawAll() {{
  const sel = Array.from(selected);
  for (const cfg of CHART_CFGS) {{
    const src = cfg.type === 'trials' ? TRIAL_DATA : SITES_DATA;
    Plotly.react(cfg.id, traces(aggregate(src, sel, cfg.phases)),
                 layout(cfg.title, yLabel(cfg.ylabel), cfg.height));
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
  if (selected.size === COMPANIES.length) {{
    selected.clear();           // all → deselect all
  }} else {{
    COMPANIES.forEach(c => selected.add(c));  // any state → select all
  }}
  syncButtons(); redrawAll();
}});

document.querySelectorAll('.co-btn[data-co]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const co = btn.dataset.co;
    if (selected.has(co)) {{
      selected.delete(co);
    }} else {{
      selected.add(co);
    }}
    syncButtons(); redrawAll();
  }});
}});

document.getElementById('btn-per-capita').addEventListener('click', () => {{
  perCapita = !perCapita;
  const btn = document.getElementById('btn-per-capita');
  btn.classList.toggle('active', perCapita);
  btn.textContent = perCapita ? 'Per Million Pop. ✓' : 'Per Million Pop.';
  redrawAll();
}});

// Init
for (const cfg of CHART_CFGS) {{
  const src = cfg.type === 'trials' ? TRIAL_DATA : SITES_DATA;
  Plotly.newPlot(cfg.id, traces(aggregate(src, COMPANIES, cfg.phases)),
                 layout(cfg.title, yLabel(cfg.ylabel), cfg.height), {{responsive:true}});
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
      display:flex; flex-wrap:nowrap; gap:6px; align-items:center; justify-content:center;
      background:#fff; border:1px solid #dce2ea; border-radius:10px;
      padding:10px 16px; margin:0 0 22px 0; overflow-x:auto;
    }}
    .filter-label {{
      font-size:12px; font-weight:700; color:#1a1a2e; margin-right:2px; white-space:nowrap;
    }}
    .co-btn {{
      padding:4px 10px; border-radius:20px; border:2px solid #c8d0db;
      background:#fff; color:#555; font-size:11px; font-weight:600;
      cursor:pointer; transition:background 0.15s, color 0.15s, border-color 0.15s;
      white-space:nowrap; flex-shrink:0;
    }}
    .co-btn:hover  {{ border-color:#0093D0; color:#0093D0; }}
    .co-btn.active {{ background:#1a1a2e; color:#fff; border-color:#1a1a2e; }}
    #btn-all        {{ border-color:#0093D0; color:#0093D0; }}
    #btn-all.active {{ background:#0093D0; color:#fff; border-color:#0093D0; }}
    #view-bar {{
      display:flex; justify-content:flex-end; margin:0 0 18px 0;
    }}
    #btn-per-capita {{
      padding:5px 14px; border-radius:20px; border:2px solid #2A9D8F;
      background:#fff; color:#2A9D8F; font-size:12px; font-weight:700;
      cursor:pointer; transition:background 0.15s, color 0.15s;
    }}
    #btn-per-capita.active {{ background:#2A9D8F; color:#fff; }}
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
  <div id="view-bar">
    <button id="btn-per-capita">Per Million Pop.</button>
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
