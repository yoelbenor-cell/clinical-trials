"""
Clinical trials dashboard — top 10 pharma, 8 countries (Israel + 7 European), 2015-2025.
Section A — Trial counts  : Phase 1 / Phase 2 / Phase 3 / All phases
Section B — Participants  : Phase 1 / Phase 2 / Phase 3 / All phases
"""
import sqlite3
import pandas as pd
import plotly.graph_objects as go

DB_PATH  = "trials.db"
MIN_YEAR = 2015
MAX_YEAR = 2025

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

PHASE_LABELS = {
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
}


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df_trials = pd.read_sql(
        "SELECT nct_id, phase, start_year, enrollment FROM trials "
        "WHERE start_year BETWEEN ? AND ? AND phase IN ('PHASE1','PHASE2','PHASE3')",
        conn, params=(MIN_YEAR, MAX_YEAR)
    )
    placeholders = ",".join("?" * len(COUNTRIES))
    df_countries = pd.read_sql(
        f"SELECT nct_id, country FROM trial_countries WHERE country IN ({placeholders})",
        conn, params=COUNTRIES
    )
    conn.close()
    df = df_trials.merge(df_countries, on="nct_id", how="inner")
    return df


def pivot_trials(df, phases):
    """Unique trial count per (year, country) for the given phases."""
    years = list(range(MIN_YEAR, MAX_YEAR + 1))
    sub   = df[df["phase"].isin(phases)]
    agg   = (
        sub.drop_duplicates(subset=["nct_id", "country"])
        .groupby(["start_year", "country"])["nct_id"]
        .count()
        .reset_index(name="cnt")
    )
    pivot = (
        agg.pivot(index="start_year", columns="country", values="cnt")
        .reindex(years, fill_value=0).fillna(0).astype(int)
    )
    for c in COUNTRIES:
        if c not in pivot.columns:
            pivot[c] = 0
    return pivot[COUNTRIES]


def pivot_enrollment(df, phases):
    """
    Sum of enrollment per (year, country).
    Each trial's enrollment is attributed fully to its start year.
    Trials with no enrollment data are excluded.
    """
    years = list(range(MIN_YEAR, MAX_YEAR + 1))
    sub   = df[df["phase"].isin(phases)].dropna(subset=["enrollment"])
    # One enrollment value per trial (deduplicate across countries first,
    # then expand to countries so each country gets the full trial enrollment)
    agg   = (
        sub.drop_duplicates(subset=["nct_id", "country"])
        .groupby(["start_year", "country"])["enrollment"]
        .sum()
        .reset_index(name="enroll")
    )
    pivot = (
        agg.pivot(index="start_year", columns="country", values="enroll")
        .reindex(years, fill_value=0).fillna(0).astype(int)
    )
    for c in COUNTRIES:
        if c not in pivot.columns:
            pivot[c] = 0
    return pivot[COUNTRIES]


def make_fig(pivot, title, y_label, height=520):
    years = list(range(MIN_YEAR, MAX_YEAR + 1))
    fig   = go.Figure()
    for country in COUNTRIES:
        fig.add_trace(go.Scatter(
            x=years,
            y=pivot[country].tolist(),
            name=country,
            mode="lines+markers",
            line=dict(color=COUNTRY_COLORS[country], width=2.5),
            marker=dict(size=7),
            hovertemplate=f"<b>{country}</b><br>Year: %{{x}}<br>{y_label}: %{{y:,}}<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=19)),
        xaxis=dict(
            title="Year", tickmode="array",
            tickvals=years, ticktext=[str(y) for y in years], tickangle=-45,
        ),
        yaxis=dict(title=y_label),
        legend=dict(title="Country", x=1.01, y=1, font=dict(size=12)),
        hovermode="x unified",
        template="plotly_white",
        height=height,
        margin=dict(r=180, t=70, b=80),
    )
    return fig


def build_dashboard():
    print("Loading data...")
    df = load_data()
    n_with_enroll = df.dropna(subset=["enrollment"])["nct_id"].nunique()
    n_total       = df["nct_id"].nunique()
    print(f"  {n_total} unique trials, {n_with_enroll} with enrollment data")

    out_path    = "pharma_trials_dashboard.html"
    html_blocks = []
    first       = True

    section_style = (
        "font-size:22px;font-weight:bold;color:#1a1a2e;"
        "border-left:5px solid #0093D0;padding-left:12px;"
        "margin:40px 0 10px 0;font-family:Arial"
    )
    header_style = (
        "font-size:26px;font-weight:bold;color:#fff;"
        "background:linear-gradient(135deg,#1a1a2e,#0093D0);"
        "padding:14px 20px;border-radius:8px;margin:30px 0 5px 0;font-family:Arial"
    )
    card_style = (
        "background:white;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.12);margin-bottom:25px;padding:15px"
    )

    def add_chart(label, fig):
        nonlocal first
        html_blocks.append(f'<div style="{section_style}">{label}</div>')
        html_blocks.append(f'<div style="{card_style}">')
        html_blocks.append(
            fig.to_html(full_html=False, include_plotlyjs=first,
                        config={"responsive": True})
        )
        html_blocks.append("</div>")
        first = False

    # ── Section A: Trial counts ──────────────────────────────────────────
    html_blocks.append(f'<div style="{header_style}">Section A — Number of Trials Started</div>')
    for phase in ["PHASE1", "PHASE2", "PHASE3"]:
        print(f"  Trials chart: {PHASE_LABELS[phase]}...")
        piv = pivot_trials(df, [phase])
        add_chart(
            PHASE_LABELS[phase],
            make_fig(piv,
                     f"<b>{PHASE_LABELS[phase]}</b> — Trials Started per Year",
                     "Number of Trials")
        )

    print("  Trials chart: Combined...")
    piv_all = pivot_trials(df, ["PHASE1", "PHASE2", "PHASE3"])
    add_chart(
        "All Phases — Combined",
        make_fig(piv_all,
                 "<b>All Phases Combined</b> — Total Trials Started per Year (Ph.1 + Ph.2 + Ph.3)",
                 "Number of Trials")
    )

    # ── Section B: Participants ──────────────────────────────────────────
    html_blocks.append(f'<div style="{header_style}">Section B — Participants Enrolled</div>')
    html_blocks.append(
        '<p style="font-family:Arial;color:#555;font-size:13px;margin:0 0 20px 4px">'
        'Each trial\'s total enrollment is attributed to its start year. '
        'Trials without enrollment data are excluded. '
        'Note: enrollment is per-trial globally — all countries in the trial share the same number.</p>'
    )

    for phase in ["PHASE1", "PHASE2", "PHASE3"]:
        print(f"  Enrollment chart: {PHASE_LABELS[phase]}...")
        piv = pivot_enrollment(df, [phase])
        add_chart(
            PHASE_LABELS[phase],
            make_fig(piv,
                     f"<b>{PHASE_LABELS[phase]}</b> — Participants Enrolled per Year",
                     "Participants")
        )

    print("  Enrollment chart: Combined...")
    piv_all_e = pivot_enrollment(df, ["PHASE1", "PHASE2", "PHASE3"])
    add_chart(
        "All Phases — Combined",
        make_fig(piv_all_e,
                 "<b>All Phases Combined</b> — Total Participants Enrolled per Year (Ph.1 + Ph.2 + Ph.3)",
                 "Participants",
                 height=560)
    )

    page_style = """
        body { font-family:Arial,sans-serif; background:#f5f7fa; margin:0; padding:20px 30px; }
        h1   { text-align:center; color:#1a1a2e; margin-bottom:4px; font-size:26px; }
        .sub { text-align:center; color:#666; margin-bottom:20px; font-size:14px; }
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pharma Clinical Trials — European Countries + Israel</title>
  <style>{page_style}</style>
</head>
<body>
  <h1>Top 10 Pharma — Clinical Trials Dashboard</h1>
  <p class="sub">
    Israel &middot; Belgium &middot; Switzerland &middot; Austria &middot;
    Sweden &middot; Denmark &middot; Norway &middot; Ireland
    &nbsp;|&nbsp; 2015&ndash;2025 &nbsp;|&nbsp; Click legend to toggle countries
  </p>
  {''.join(html_blocks)}
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nSaved: {out_path}  ({len(html)//1024} KB)")
    return out_path


if __name__ == "__main__":
    build_dashboard()
