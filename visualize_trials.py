"""
Clinical trials dashboard — top 10 pharma, 31 European countries + Israel, 2015-2025.
Interactive: filter by company, filter by country (presets + custom), per-capita toggle.
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

ALL_COUNTRIES = [
    "Israel",
    "Germany", "France", "United Kingdom", "Italy", "Spain", "Poland",
    "Netherlands", "Belgium", "Sweden", "Austria", "Denmark", "Finland",
    "Czechia", "Romania", "Hungary", "Portugal", "Greece", "Slovakia",
    "Bulgaria", "Croatia", "Lithuania", "Latvia", "Estonia", "Slovenia",
    "Cyprus", "Luxembourg", "Malta", "Norway", "Iceland", "Switzerland",
]

COUNTRY_COLORS = {
    "Israel":         "#0038B8",
    "Germany":        "#555555",
    "France":         "#4169E1",
    "United Kingdom": "#C60C30",
    "Italy":          "#009246",
    "Spain":          "#FF8C00",
    "Poland":         "#DC143C",
    "Netherlands":    "#FF6600",
    "Belgium":        "#E63946",
    "Sweden":         "#006AA7",
    "Austria":        "#EF3340",
    "Denmark":        "#C8102E",
    "Finland":        "#003680",
    "Czechia":        "#8B4513",
    "Romania":        "#4682B4",
    "Hungary":        "#00843D",
    "Portugal":       "#006400",
    "Greece":         "#0D5EAF",
    "Slovakia":       "#6B8E23",
    "Bulgaria":       "#2A9D8F",
    "Croatia":        "#FF69B4",
    "Lithuania":      "#FDB913",
    "Latvia":         "#9B2335",
    "Estonia":        "#00BFFF",
    "Slovenia":       "#556B2F",
    "Cyprus":         "#DAA520",
    "Luxembourg":     "#F4A460",
    "Malta":          "#CD853F",
    "Norway":         "#EF2B2D",
    "Iceland":        "#6495ED",
    "Switzerland":    "#FF4500",
}

# Population in millions, 2015-2025 — World Bank WDI (2024-2025: estimates)
POPULATION = {
    #                      2015   2016   2017   2018   2019   2020   2021   2022   2023   2024   2025
    "Israel":          [8.38,  8.54,  8.71,  8.88,  9.05,  9.22,  9.45,  9.66,  9.84, 10.01, 10.20],
    "Germany":         [81.69, 82.18, 82.66, 83.02, 83.15, 83.24, 83.20, 84.08, 84.36, 84.50, 84.60],
    "France":          [64.40, 64.73, 65.02, 65.27, 65.56, 65.85, 66.32, 67.37, 68.02, 68.40, 68.70],
    "United Kingdom":  [65.13, 65.65, 66.06, 66.44, 66.80, 67.08, 67.22, 67.60, 67.74, 67.90, 68.10],
    "Italy":           [60.80, 60.65, 60.58, 60.48, 60.24, 59.64, 59.24, 58.97, 58.85, 58.60, 58.40],
    "Spain":           [46.45, 46.48, 46.53, 46.66, 46.94, 47.35, 47.40, 47.42, 47.42, 47.50, 47.60],
    "Poland":          [37.99, 37.97, 37.97, 37.98, 37.97, 37.95, 37.75, 37.65, 37.63, 37.55, 37.50],
    "Netherlands":     [16.90, 16.99, 17.08, 17.18, 17.28, 17.41, 17.48, 17.59, 17.88, 18.00, 18.10],
    "Belgium":         [11.24, 11.31, 11.35, 11.43, 11.51, 11.59, 11.59, 11.66, 11.74, 11.87, 11.95],
    "Sweden":          [9.80,  9.92, 10.07, 10.18, 10.29, 10.33, 10.42, 10.52, 10.55, 10.65, 10.75],
    "Austria":         [8.66,  8.74,  8.80,  8.85,  8.90,  8.93,  9.04,  9.10,  9.10,  9.15,  9.21],
    "Denmark":         [5.69,  5.73,  5.75,  5.80,  5.81,  5.82,  5.84,  5.88,  5.96,  6.03,  6.10],
    "Finland":         [5.47,  5.49,  5.51,  5.52,  5.52,  5.53,  5.54,  5.56,  5.57,  5.58,  5.60],
    "Czechia":         [10.55, 10.57, 10.61, 10.65, 10.67, 10.70, 10.79, 10.83, 10.88, 10.90, 10.95],
    "Romania":         [19.87, 19.67, 19.54, 19.47, 19.36, 19.26, 18.95, 19.03, 18.88, 18.70, 18.55],
    "Hungary":         [9.84,  9.80,  9.77,  9.77,  9.77,  9.75,  9.71,  9.69,  9.68,  9.65,  9.62],
    "Portugal":        [10.34, 10.31, 10.29, 10.28, 10.27, 10.30, 10.33, 10.34, 10.24, 10.20, 10.15],
    "Greece":          [10.84, 10.76, 10.72, 10.73, 10.72, 10.72, 10.68, 10.62, 10.43, 10.40, 10.38],
    "Slovakia":        [5.42,  5.43,  5.44,  5.45,  5.46,  5.46,  5.46,  5.46,  5.47,  5.48,  5.50],
    "Bulgaria":        [7.15,  7.10,  7.05,  6.97,  6.90,  6.52,  6.52,  6.52,  6.45,  6.40,  6.35],
    "Croatia":         [4.20,  4.17,  4.15,  4.09,  4.07,  4.05,  3.89,  3.88,  3.86,  3.85,  3.84],
    "Lithuania":       [2.92,  2.89,  2.85,  2.81,  2.79,  2.79,  2.81,  2.89,  2.92,  2.93,  2.94],
    "Latvia":          [2.00,  1.97,  1.95,  1.93,  1.92,  1.91,  1.85,  1.83,  1.82,  1.82,  1.83],
    "Estonia":         [1.31,  1.31,  1.32,  1.32,  1.33,  1.33,  1.33,  1.37,  1.37,  1.37,  1.38],
    "Slovenia":        [2.06,  2.07,  2.07,  2.07,  2.09,  2.10,  2.11,  2.11,  2.12,  2.12,  2.13],
    "Cyprus":          [1.17,  1.17,  1.18,  1.19,  1.20,  1.21,  1.22,  1.26,  1.26,  1.28,  1.30],
    "Luxembourg":      [0.57,  0.58,  0.59,  0.61,  0.63,  0.63,  0.63,  0.65,  0.67,  0.68,  0.69],
    "Malta":           [0.44,  0.46,  0.47,  0.48,  0.50,  0.52,  0.52,  0.53,  0.53,  0.54,  0.55],
    "Norway":          [5.19,  5.23,  5.27,  5.30,  5.33,  5.37,  5.41,  5.43,  5.52,  5.59,  5.67],
    "Iceland":         [0.33,  0.34,  0.34,  0.35,  0.36,  0.37,  0.37,  0.37,  0.37,  0.37,  0.38],
    "Switzerland":     [8.33,  8.40,  8.48,  8.55,  8.60,  8.67,  8.74,  8.82,  8.96,  9.10,  9.18],
}

# GDP per capita 2023, nominal USD — World Bank / IMF
GDP_PER_CAPITA = {
    "Israel":         54000, "Germany":        54000, "France":         43000,
    "United Kingdom": 46000, "Italy":          36000, "Spain":          32000,
    "Poland":         22000, "Netherlands":    58000, "Belgium":        51000,
    "Sweden":         55000, "Austria":        56000, "Denmark":        68000,
    "Finland":        53000, "Czechia":        27000, "Romania":        16000,
    "Hungary":        19000, "Portugal":       25000, "Greece":         22000,
    "Slovakia":       21000, "Bulgaria":       14000, "Croatia":        21000,
    "Lithuania":      26000, "Latvia":         21000, "Estonia":        29000,
    "Slovenia":       32000, "Cyprus":         32000, "Luxembourg":    131000,
    "Malta":          34000, "Norway":        106000, "Iceland":        76000,
    "Switzerland":    93000,
}

# Preset groups (computed in Python, embedded as JSON)
POP_2023 = {c: POPULATION[c][8] for c in ALL_COUNTRIES}  # index 8 = 2023
IRELAND_POP  = POP_2023["Ireland"]   if "Ireland" in POP_2023 else 5.31
BELGIUM_POP  = POP_2023["Belgium"]   if "Belgium" in POP_2023 else 11.74

PRESET_SIMILAR_POP    = sorted([c for c in ALL_COUNTRIES
                                 if IRELAND_POP <= POP_2023[c] <= BELGIUM_POP])
PRESET_HIGH_GDP       = sorted([c for c in ALL_COUNTRIES if GDP_PER_CAPITA[c] >= 40000])
PRESET_SIMILAR_ISRAEL = sorted([c for c in ALL_COUNTRIES
                                 if c in PRESET_SIMILAR_POP and c in PRESET_HIGH_GDP])

PHASES = ["PHASE1", "PHASE2", "PHASE3"]
YEARS  = list(range(MIN_YEAR, MAX_YEAR + 1))


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_trials = pd.read_sql(
        "SELECT nct_id, company, phase, start_year FROM trials "
        "WHERE start_year BETWEEN ? AND ? AND phase IN ('PHASE1','PHASE2','PHASE3')",
        conn, params=(MIN_YEAR, MAX_YEAR),
    )
    placeholders = ",".join("?" * len(ALL_COUNTRIES))
    df_countries = pd.read_sql(
        f"SELECT nct_id, country, COALESCE(site_count, 1) AS site_count "
        f"FROM trial_countries WHERE country IN ({placeholders})",
        conn, params=ALL_COUNTRIES,
    )
    conn.close()
    return df_trials.merge(df_countries, on="nct_id", how="inner")


def build_company_data(df):
    empty = lambda: {co: {ph: {ct: {yr: 0 for yr in YEARS}
                               for ct in ALL_COUNTRIES}
                          for ph in PHASES}
                    for co in COMPANIES}

    trial_data = empty()
    sites_data = empty()

    trial_agg = (
        df.groupby(["company", "phase", "country", "start_year"])["nct_id"]
        .nunique().reset_index(name="cnt")
    )
    sites_agg = (
        df.groupby(["company", "phase", "country", "start_year"])["site_count"]
        .sum().reset_index(name="sites")
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
    print(f"  {df['nct_id'].nunique()} unique trials, "
          f"{df['country'].nunique()} countries loaded")

    print("Building per-company data matrices...")
    trial_data, sites_data = build_company_data(df)

    SECTION_A = "Section A — Number of Trials Started"
    SECTION_B = "Section B — Research Sites per Country"

    chart_configs = []
    for ph in PHASES:
        label = ph.replace("PHASE", "Phase ")
        chart_configs.append({"id": f"chart_{ph.lower()}_trials", "section": SECTION_A,
            "label": label, "type": "trials", "phases": [ph],
            "title": f"<b>{label}</b> — Trials Started per Year", "ylabel": "Number of Trials", "height": 520})
    chart_configs.append({"id": "chart_all_trials", "section": SECTION_A,
        "label": "All Phases — Combined", "type": "trials", "phases": PHASES,
        "title": "<b>All Phases Combined</b> — Total Trials Started per Year (Ph.1+Ph.2+Ph.3)",
        "ylabel": "Number of Trials", "height": 520})

    for ph in PHASES:
        label = ph.replace("PHASE", "Phase ")
        chart_configs.append({"id": f"chart_{ph.lower()}_sites", "section": SECTION_B,
            "label": label, "type": "sites", "phases": [ph],
            "title": f"<b>{label}</b> — Research Sites per Year", "ylabel": "Research Sites", "height": 520})
    chart_configs.append({"id": "chart_all_sites", "section": SECTION_B,
        "label": "All Phases — Combined", "type": "sites", "phases": PHASES,
        "title": "<b>All Phases Combined</b> — Total Research Sites per Year (Ph.1+Ph.2+Ph.3)",
        "ylabel": "Research Sites", "height": 560})

    header_style = ("font-size:26px;font-weight:bold;color:#fff;"
        "background:linear-gradient(135deg,#1a1a2e,#0093D0);"
        "padding:14px 20px;border-radius:8px;margin:30px 0 5px 0;font-family:Arial")
    sub_style = ("font-size:22px;font-weight:bold;color:#1a1a2e;"
        "border-left:5px solid #0093D0;padding-left:12px;"
        "margin:40px 0 10px 0;font-family:Arial")
    card_style = ("background:white;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.12);margin-bottom:25px;padding:15px")

    body_blocks = []
    current_section = None
    for cfg in chart_configs:
        if cfg["section"] != current_section:
            current_section = cfg["section"]
            body_blocks.append(f'<div style="{header_style}">{current_section}</div>')
            if current_section == SECTION_B:
                body_blocks.append(
                    '<p style="font-family:Arial;color:#555;font-size:13px;margin:0 0 20px 4px">'
                    'Number of active research sites (locations) per country per year. '
                    'Source: ClinicalTrials.gov location data.</p>')
        body_blocks.append(f'<div style="{sub_style}">{cfg["label"]}</div>')
        body_blocks.append(f'<div style="{card_style}"><div id="{cfg["id"]}"></div></div>')

    company_buttons = '<button id="btn-all" class="co-btn active">All</button>\n    ' + "\n    ".join(
        f'<button class="co-btn active" data-co="{co}">{co}</button>' for co in COMPANIES)

    country_checkboxes = "\n".join(
        f'<label class="ct-check"><input type="checkbox" value="{ct}" checked> {ct}</label>'
        for ct in sorted(ALL_COUNTRIES))

    js = f"""
const TRIAL_DATA  = {json.dumps(trial_data)};
const SITES_DATA  = {json.dumps(sites_data)};
const COMPANIES   = {json.dumps(COMPANIES)};
const ALL_CTRS    = {json.dumps(ALL_COUNTRIES)};
const COLORS      = {json.dumps(COUNTRY_COLORS)};
const YEARS       = {json.dumps(YEARS)};
const CHART_CFGS  = {json.dumps(chart_configs)};
const POPULATION  = {json.dumps(POPULATION)};
const GDP_PC      = {json.dumps(GDP_PER_CAPITA)};
const POP_2023    = {json.dumps(POP_2023)};
const P_SIM_POP   = {json.dumps(PRESET_SIMILAR_POP)};
const P_HIGH_GDP  = {json.dumps(PRESET_HIGH_GDP)};
const P_SIM_ISR   = {json.dumps(PRESET_SIMILAR_ISRAEL)};

let selected    = new Set(COMPANIES);
let selCtrs     = new Set(ALL_CTRS);
let perCapita   = false;

/* ── aggregate ────────────────────────────────────────────── */
function aggregate(dataObj, companies, phases) {{
  const result = {{}};
  for (const ct of selCtrs) {{
    result[ct] = YEARS.map((yr, i) => {{
      let s = 0;
      for (const co of companies)
        for (const ph of phases)
          s += (dataObj[co]?.[ph]?.[ct]?.[yr]) || 0;
      if (perCapita) {{
        const pop = POPULATION[ct]?.[i];
        return pop ? +((s / pop).toFixed(3)) : 0;
      }}
      return s;
    }});
  }}
  return result;
}}

function traces(agg) {{
  return Array.from(selCtrs).map(ct => ({{
    x: YEARS, y: agg[ct] || YEARS.map(() => 0), name: ct,
    mode: 'lines+markers',
    line: {{color: COLORS[ct] || '#888', width: 2}},
    marker: {{size: 6}},
    type: 'scatter',
    hovertemplate: '<b>' + ct + '</b><br>Year: %{{x}}<br>' +
                   (perCapita ? 'Value: %{{y:.3f}}' : 'Value: %{{y:,}}') +
                   '<extra></extra>',
  }}));
}}

function layout(title, ylabel, height) {{
  return {{
    title: {{text: title, font: {{size: 18}}}},
    xaxis: {{title:'Year', tickmode:'array', tickvals:YEARS,
             ticktext:YEARS.map(String), tickangle:-45}},
    yaxis: {{title: ylabel}},
    legend: {{title:{{text:'Country'}}, x:1.01, y:1, font:{{size:11}}}},
    hovermode: 'x unified', template: 'plotly_white',
    height: height, margin: {{r:180, t:60, b:80}},
  }};
}}

function yLabel(base) {{
  return perCapita ? base + ' per Million Pop.' : base;
}}

function redrawAll() {{
  const sel = Array.from(selected);
  for (const cfg of CHART_CFGS) {{
    const src = cfg.type === 'trials' ? TRIAL_DATA : SITES_DATA;
    Plotly.react(cfg.id, traces(aggregate(src, sel, cfg.phases)),
                 layout(cfg.title, yLabel(cfg.ylabel), cfg.height));
  }}
}}

/* ── Company buttons ──────────────────────────────────────── */
function syncCoBtns() {{
  const all = selected.size === COMPANIES.length;
  document.getElementById('btn-all').classList.toggle('active', all);
  document.querySelectorAll('.co-btn[data-co]').forEach(b =>
    b.classList.toggle('active', selected.has(b.dataset.co)));
}}

document.getElementById('btn-all').addEventListener('click', () => {{
  if (selected.size === COMPANIES.length) selected.clear();
  else COMPANIES.forEach(c => selected.add(c));
  syncCoBtns(); redrawAll();
}});
document.querySelectorAll('.co-btn[data-co]').forEach(btn =>
  btn.addEventListener('click', () => {{
    const co = btn.dataset.co;
    selected.has(co) ? selected.delete(co) : selected.add(co);
    syncCoBtns(); redrawAll();
  }}));

/* ── Country presets ──────────────────────────────────────── */
function applyPreset(preset, btnId) {{
  selCtrs = new Set(preset);
  // sync checkboxes
  document.querySelectorAll('.ct-check input').forEach(cb => {{
    cb.checked = selCtrs.has(cb.value);
  }});
  // highlight active preset
  document.querySelectorAll('.preset-btn').forEach(b =>
    b.classList.remove('active'));
  if (btnId) document.getElementById(btnId).classList.add('active');
  redrawAll();
}}

document.getElementById('preset-all').addEventListener('click',
  () => applyPreset(ALL_CTRS, 'preset-all'));
document.getElementById('preset-gdp').addEventListener('click',
  () => applyPreset(P_HIGH_GDP, 'preset-gdp'));
document.getElementById('preset-pop').addEventListener('click',
  () => applyPreset(P_SIM_POP, 'preset-pop'));
document.getElementById('preset-isr').addEventListener('click',
  () => applyPreset(P_SIM_ISR, 'preset-isr'));

/* ── Country dropdown ─────────────────────────────────────── */
const dropdown = document.getElementById('country-dropdown');
document.getElementById('preset-select').addEventListener('click', (e) => {{
  e.stopPropagation();
  dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
}});
document.addEventListener('click', (e) => {{
  if (!dropdown.contains(e.target) && e.target.id !== 'preset-select')
    dropdown.style.display = 'none';
}});

document.getElementById('dd-all').addEventListener('click', () =>
  document.querySelectorAll('.ct-check input').forEach(cb => cb.checked = true));
document.getElementById('dd-none').addEventListener('click', () =>
  document.querySelectorAll('.ct-check input').forEach(cb => cb.checked = false));
document.getElementById('dd-apply').addEventListener('click', () => {{
  selCtrs = new Set(
    [...document.querySelectorAll('.ct-check input:checked')].map(cb => cb.value));
  if (selCtrs.size === 0) selCtrs = new Set(ALL_CTRS);
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  dropdown.style.display = 'none';
  redrawAll();
}});

/* ── Per-capita toggle ────────────────────────────────────── */
document.getElementById('btn-per-capita').addEventListener('click', () => {{
  perCapita = !perCapita;
  const btn = document.getElementById('btn-per-capita');
  btn.classList.toggle('active', perCapita);
  btn.textContent = perCapita ? 'Per Million Pop. ✓' : 'Per Million Pop.';
  redrawAll();
}});

/* ── Init ─────────────────────────────────────────────────── */
for (const cfg of CHART_CFGS) {{
  const src = cfg.type === 'trials' ? TRIAL_DATA : SITES_DATA;
  Plotly.newPlot(cfg.id, traces(aggregate(src, COMPANIES, cfg.phases)),
                 layout(cfg.title, yLabel(cfg.ylabel), cfg.height), {{responsive:true}});
}}
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pharma Clinical Trials — Europe + Israel</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body   {{ font-family:Arial,sans-serif; background:#f5f7fa; margin:0; padding:20px 30px; }}
    h1     {{ text-align:center; color:#1a1a2e; margin-bottom:4px; font-size:26px; }}
    .sub   {{ text-align:center; color:#666; margin-bottom:14px; font-size:14px; }}

    /* Company filter */
    #filter-bar {{
      display:flex; flex-wrap:nowrap; gap:6px; align-items:center;
      justify-content:center; background:#fff; border:1px solid #dce2ea;
      border-radius:10px; padding:10px 16px; margin:0 0 10px 0; overflow-x:auto;
    }}
    .filter-label {{ font-size:12px; font-weight:700; color:#1a1a2e; margin-right:2px; white-space:nowrap; }}
    .co-btn {{
      padding:4px 10px; border-radius:20px; border:2px solid #c8d0db;
      background:#fff; color:#555; font-size:11px; font-weight:600;
      cursor:pointer; transition:background .15s,color .15s,border-color .15s;
      white-space:nowrap; flex-shrink:0;
    }}
    .co-btn:hover  {{ border-color:#0093D0; color:#0093D0; }}
    .co-btn.active {{ background:#1a1a2e; color:#fff; border-color:#1a1a2e; }}
    #btn-all        {{ border-color:#0093D0; color:#0093D0; }}
    #btn-all.active {{ background:#0093D0; color:#fff; border-color:#0093D0; }}

    /* Country preset bar */
    #country-bar {{
      display:flex; flex-wrap:wrap; gap:7px; align-items:center;
      background:#fff; border:1px solid #dce2ea; border-radius:10px;
      padding:10px 16px; margin:0 0 10px 0; position:relative;
    }}
    .preset-label {{ font-size:12px; font-weight:700; color:#1a1a2e; margin-right:2px; }}
    .preset-btn {{
      padding:5px 13px; border-radius:20px; border:2px solid #c8d0db;
      background:#fff; color:#555; font-size:12px; font-weight:600;
      cursor:pointer; transition:background .15s,color .15s,border-color .15s;
      white-space:nowrap;
    }}
    .preset-btn:hover  {{ border-color:#0093D0; color:#0093D0; }}
    .preset-btn.active {{ background:#1a1a2e; color:#fff; border-color:#1a1a2e; }}
    #preset-all.active {{ background:#0093D0; border-color:#0093D0; }}
    #preset-select {{ border-color:#7B61FF; color:#7B61FF; }}
    #preset-select:hover {{ background:#7B61FF; color:#fff; }}

    /* Dropdown */
    #country-dropdown {{
      display:none; position:absolute; top:calc(100% + 6px); left:0; right:0;
      z-index:999; background:#fff; border:1px solid #dce2ea;
      border-radius:10px; box-shadow:0 4px 20px rgba(0,0,0,0.15);
      padding:14px 16px 10px;
    }}
    #country-grid {{
      display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
      gap:4px 12px; max-height:260px; overflow-y:auto; margin-bottom:10px;
    }}
    .ct-check {{ font-size:12px; color:#333; display:flex; align-items:center; gap:5px; cursor:pointer; }}
    .ct-check input {{ cursor:pointer; }}
    .dd-actions {{ display:flex; gap:8px; justify-content:flex-end; }}
    .dd-btn {{
      padding:5px 14px; border-radius:6px; border:1px solid #c8d0db;
      background:#f5f7fa; font-size:12px; font-weight:600; cursor:pointer;
    }}
    #dd-apply {{ background:#1a1a2e; color:#fff; border-color:#1a1a2e; }}

    /* Per-capita */
    #view-bar {{ display:flex; justify-content:flex-end; margin:0 0 18px 0; }}
    #btn-per-capita {{
      padding:5px 14px; border-radius:20px; border:2px solid #2A9D8F;
      background:#fff; color:#2A9D8F; font-size:12px; font-weight:700; cursor:pointer;
    }}
    #btn-per-capita.active {{ background:#2A9D8F; color:#fff; }}
  </style>
</head>
<body>
  <h1>Top 10 Pharma — Clinical Trials Dashboard</h1>
  <p class="sub">
    Europe + Israel &nbsp;|&nbsp; 2015&ndash;2025 &nbsp;|&nbsp;
    Click legend to toggle &nbsp;|&nbsp;
    Data source:&nbsp;<a href="https://clinicaltrials.gov" target="_blank"
      style="color:#0093D0;text-decoration:none;font-weight:bold;">ClinicalTrials.gov</a>
  </p>

  <!-- Company filter -->
  <div id="filter-bar">
    <span class="filter-label">Filter by Company:</span>
    {company_buttons}
  </div>

  <!-- Country preset bar (with relative positioning for dropdown) -->
  <div id="country-bar">
    <span class="preset-label">Countries:</span>
    <button class="preset-btn active" id="preset-all">All ({len(ALL_COUNTRIES)})</button>
    <button class="preset-btn" id="preset-gdp">High GDP (&gt;$40k) &mdash; {len(PRESET_HIGH_GDP)} countries</button>
    <button class="preset-btn" id="preset-pop">Pop {IRELAND_POP:.1f}M&ndash;{BELGIUM_POP:.1f}M &mdash; {len(PRESET_SIMILAR_POP)} countries</button>
    <button class="preset-btn" id="preset-isr">Similar to Israel &mdash; {len(PRESET_SIMILAR_ISRAEL)} countries</button>
    <button class="preset-btn" id="preset-select">Select Countries &#9660;</button>

    <!-- Dropdown (inside country-bar for relative positioning) -->
    <div id="country-dropdown">
      <div id="country-grid">
{country_checkboxes}
      </div>
      <div class="dd-actions">
        <button class="dd-btn" id="dd-all">Select All</button>
        <button class="dd-btn" id="dd-none">Clear</button>
        <button class="dd-btn" id="dd-apply">Apply</button>
      </div>
    </div>
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
    print(f"\nSaved: {OUT_PATH}  ({len(html)//1024} KB)")
    print(f"Presets: high-GDP={len(PRESET_HIGH_GDP)}, "
          f"similar-pop={len(PRESET_SIMILAR_POP)}, "
          f"similar-israel={len(PRESET_SIMILAR_ISRAEL)}")


if __name__ == "__main__":
    build_dashboard()
