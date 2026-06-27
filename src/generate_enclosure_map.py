#!/usr/bin/env python3
"""
Generate choropleth map(s) of "enclosure strength" (RTLP R score, 0-1) across the 193 UN Member States.

Uses Mollweide (equal-area) projection for the world view (good area preservation for choropleths).
True Dymaxion or Goode's butterfly/interrupted projections are not supported by Plotly's geo engine;
Mollweide is the recommended low-distortion alternative within the current stack.

Uses the pre-built 2026 ATLAS data (R computed from 8 V-Dem 2024 indicators + 1 real WB socioeconomic per the source crosswalk;
G₀ = 2026-fresh GDP per capita as the more dynamic variable per project rule).

Outputs (to outputs/figures/):
- rtl_di_enclosure_strength_2026_choropleth.png  (high-res static for print / ebook)
- rtl_di_enclosure_strength_2026_choropleth.pdf  (vector)
- rtl_di_enclosure_strength_2026_choropleth.html (interactive with hover for all details)

Usage:
  python3 -m src.generate_enclosure_map
  # or with year override (future data)
  python3 -m src.generate_enclosure_map --year 2026 --input outputs/atlas/rtl_di_atlas_un_members_2026.csv

Requires (beyond core atlas): plotly (already in some envs), kaleido (for static export).
Add to pip:  pip install plotly kaleido

The map visualizes "enclosure strength" directly as the RTLP R from the source document
(Hubbard 2026V3): higher R = stronger protection of the right to life within the nested causal enclosures.

Fidelity: exactly 193 UN members, R in [0,1], vintage labels on every artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.express as px

# Default output base (committed as demo per .gitignore whitelist)
DEFAULT_ATLAS_CSV = "outputs/atlas/rtl_di_atlas_un_members_2026.csv"
OUT_DIR = Path("outputs/figures")
BASE_NAME = "rtl_di_enclosure_strength_2026_choropleth"
DETAIL_JSON = Path("data/processed/rtl_di_nation_breakdown_2026.json")


def load_atlas_for_map(path: str | None = None) -> pd.DataFrame:
    """Load the master atlas table and keep only columns needed for the choropleth + hover."""
    csv_path = Path(path) if path else Path(DEFAULT_ATLAS_CSV)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Atlas CSV not found at {csv_path}. Run `python -m src.build_atlas --year 2026` first."
        )
    df = pd.read_csv(csv_path)

    # Standardize / select
    keep = ["iso3", "country", "UNregion", "r", "g0", "g0_year", "vdem_year",
            "delta_g_per_capita", "total_deficit_usd", "population", "rank_by_r_lowest"]
    cols = [c for c in keep if c in df.columns]
    df = df[cols].copy()

    # Drop rows without usable R or iso3 (should be none for 193)
    df = df.dropna(subset=["r", "iso3"])
    df["iso3"] = df["iso3"].astype(str).str.upper()

    # Ensure r is float in [0,1]
    df["r"] = pd.to_numeric(df["r"], errors="coerce")
    df = df[(df["r"] >= 0) & (df["r"] <= 1)]

    print(f"Loaded {len(df)} countries with valid R from {csv_path}")
    return df


def make_choropleth(df: pd.DataFrame, atlas_year: int = 2026) -> px.choropleth:
    """Build a clean, publication-grade choropleth figure with full vintage/source annotation."""
    # Title + subtitle
    title = (
        f"Enclosure Strength (RTLP R) — UN Member States<br>"
        f"<sub>RTLDI ATLAS {atlas_year} | R = Right-to-Life Protection score (0 = weakest, 1 = strongest)</sub>"
    )

    fig = px.choropleth(
        df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale="Viridis",
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={
            "r": ":.3f",
            "UNregion": True,
            "vdem_year": True,
            "g0_year": True,
            "delta_g_per_capita": ":.2f",
            "total_deficit_usd": ":.0f",
            "population": ":,.0f",
        },
        labels={
            "r": "Enclosure Strength R",
            "UNregion": "UN Region",
            "vdem_year": "V-Dem year",
            "g0_year": "GDP baseline year",
            "delta_g_per_capita": "ΔG per capita (USD)",
            "total_deficit_usd": "Total annual capital exclusions (USD)",
            "population": "Population",
        },
    )

    # Improve geo aesthetics and projection.
    # Using "mollweide" (equal-area pseudocylindrical) for better area preservation
    # in a world choropleth than the previous "natural earth".
    # Note: True Dymaxion (icosahedral/butterfly) or Goode's interrupted homolosine
    # are not supported in Plotly's built-in geo projections. Mollweide is a strong
    # low-distortion choice for thematic maps of enclosure strength.
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="rgba(180,180,180,0.6)",
        showland=True,
        landcolor="rgba(245,245,245,0.9)",
        showocean=True,
        oceancolor="rgba(230,242,255,0.6)",
        showlakes=True,
        lakecolor="rgba(230,242,255,0.6)",
        projection_type="mollweide",
        lataxis_showgrid=False,
        lonaxis_showgrid=False,
        framecolor="rgba(150,150,150,0.5)",
    )

    # Colorbar styling
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="Enclosure<br>Strength R<br>(0–1)", font=dict(size=11)),
            tickmode="array",
            tickvals=[0.0, 0.25, 0.5, 0.75, 1.0],
            ticktext=["0.00", "0.25", "0.50", "0.75", "1.00"],
            len=0.6,
            thickness=12,
        ),
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
        margin=dict(l=10, r=10, t=70, b=95),
        height=820,
        width=1380,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    # Prominent data vintage + source footnote (visible in static exports)
    # Positioned below the map area
    note = (
        "R from 8 V-Dem components (crosswalk, year=2024) + 1 World Bank socioeconomic indicator (#9) + 2026-fresh G₀ (GDP per capita current US$). "
        "GDP is the more dynamic variable; V-Dem RTLP components use the file's latest available year (2024). "
        "ΔG = 0.05 × (1 − R) × G₀ per Hubbard (2026V3). Source: 10.5281/zenodo.19468550 | 193 UN Member States."
    )
    fig.add_annotation(
        text=note,
        x=0.5,
        y=-0.035,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=8.5, color="#444444"),
        align="center",
        bordercolor="rgba(200,200,200,0.4)",
        borderwidth=0.5,
        borderpad=3,
        bgcolor="rgba(255,255,255,0.85)",
    )

    # Small footer credit line (right side, subtle)
    fig.add_annotation(
        text="RTLDI ATLAS 2026 — generated from exact equations in Causality and Attraction v3 (Hubbard)",
        x=0.99,
        y=0.005,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=7, color="#888888"),
        align="right",
    )

    return fig


def _clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def build_country_payload(df: pd.DataFrame) -> dict:
    """Build compact per-country data for the click-through explorer panel."""
    details = {}
    if DETAIL_JSON.exists():
        with open(DETAIL_JSON) as f:
            for row in json.load(f):
                details[str(row.get("iso3", "")).upper()] = row

    payload = {}
    for _, row in df.iterrows():
        iso3 = str(row.get("iso3", "")).upper()
        detail = details.get(iso3, {})
        components = []
        for comp in detail.get("components", []):
            components.append({
                "num": _clean_value(comp.get("num")),
                "name": _clean_value(comp.get("name")),
                "raw": _clean_value(comp.get("raw")),
                "thresh": _clean_value(comp.get("thresh")),
                "bin": int(comp.get("bin", 0) or 0),
                "yes": _clean_value(comp.get("yes")),
                "desc": _clean_value(comp.get("desc")),
            })

        payload[iso3] = {
            "iso3": iso3,
            "country": _clean_value(row.get("country") or detail.get("country") or iso3),
            "region": _clean_value(row.get("UNregion") or detail.get("un_region") or ""),
            "r": _clean_value(row.get("r")),
            "g0": _clean_value(row.get("g0")),
            "g0_year": _clean_value(row.get("g0_year")),
            "vdem_year": _clean_value(row.get("vdem_year")),
            "delta_g_per_capita": _clean_value(row.get("delta_g_per_capita")),
            "total_deficit_usd": _clean_value(row.get("total_deficit_usd")),
            "population": _clean_value(row.get("population")),
            "rank_by_r_lowest": _clean_value(row.get("rank_by_r_lowest")),
            "components": components,
        }
    return payload


def build_interactive_html(fig, df: pd.DataFrame, atlas_year: int = 2026) -> str:
    """Wrap the Plotly map with a click-driven national data explorer."""
    countries = build_country_payload(df)
    plot_html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        div_id="rtldi-map",
        config={"responsive": True, "displaylogo": False},
    )
    countries_json = json.dumps(countries, ensure_ascii=False, allow_nan=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>RTLDI ATLAS {atlas_year} — Interactive Map Explorer</title>
<style>
  :root {{
    --ink: #18202b;
    --muted: #5b6770;
    --rule: #c6d1da;
    --panel: #f7fafc;
    --accent: #107e65;
    --blue: #1f4e79;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #eef2f5;
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .shell {{
    width: min(1440px, 100%);
    margin: 0 auto;
    background: #fff;
    min-height: 100vh;
  }}
  header {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(255,255,255,.96);
    border-bottom: 1px solid #d8e0e7;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }}
  h1 {{
    margin: 0;
    font-size: 24px;
    line-height: 1.1;
    font-weight: 650;
    letter-spacing: 0;
  }}
  .subhead {{
    margin-top: 4px;
    color: var(--muted);
    font-size: 12px;
  }}
  .actions {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
  }}
  .button {{
    border: 1px solid #cbd5df;
    background: #fff;
    color: var(--ink);
    padding: 8px 10px;
    font-size: 13px;
    text-decoration: none;
  }}
  .button.primary {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }}
  main {{ padding: 18px 24px 28px; }}
  .map-frame {{
    border: 1px solid #d8e0e7;
    background: #fff;
    overflow: hidden;
  }}
  #rtldi-map {{
    width: 100% !important;
    height: min(68vh, 780px) !important;
  }}
  .hint {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid #d8e0e7;
    border-top: 0;
    padding: 10px 12px;
    font-size: 12px;
    color: var(--muted);
    background: #f8fafc;
  }}
  #country-panel {{
    margin-top: 18px;
    border: 1px solid #d8e0e7;
    background: #fff;
  }}
  .empty {{
    padding: 28px;
    color: var(--muted);
    background: var(--panel);
  }}
  .panel-head {{
    border-bottom: 1px solid #d8e0e7;
    background: #f8fafc;
    padding: 18px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 12px;
  }}
  .panel-title {{
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
    font-weight: 650;
  }}
  .panel-meta {{
    margin-top: 6px;
    color: var(--muted);
    font-size: 13px;
  }}
  .r-badge {{
    align-self: start;
    min-width: 90px;
    border-left: 4px solid var(--accent);
    background: #edf7f4;
    padding: 10px 12px;
    text-align: right;
  }}
  .r-badge span {{
    display: block;
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
  }}
  .r-badge strong {{
    display: block;
    font-size: 30px;
    line-height: 1;
  }}
  .metrics {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    padding: 14px 18px;
    border-bottom: 1px solid #d8e0e7;
  }}
  .metric {{
    border: 1px solid #d8e0e7;
    background: var(--panel);
    padding: 12px;
    min-height: 78px;
  }}
  .metric label {{
    display: block;
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}
  .metric strong {{
    font-size: 24px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }}
  .detail-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr);
    gap: 18px;
    padding: 18px;
  }}
  .section-label {{
    color: var(--blue);
    font-size: 12px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .components {{
    display: grid;
    gap: 8px;
  }}
  .component {{
    border: 1px solid #d8e0e7;
    padding: 10px;
    background: #fff;
  }}
  .component-top {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-size: 13px;
  }}
  .status {{
    flex: 0 0 auto;
    font-size: 11px;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid #d8e0e7;
  }}
  .status.yes {{
    color: #166534;
    background: #f0fdf4;
    border-color: #bbf7d0;
  }}
  .status.no {{
    color: #991b1b;
    background: #fff1f2;
    border-color: #fecdd3;
  }}
  .component-desc {{
    margin-top: 5px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.4;
  }}
  .raw {{
    margin-top: 5px;
    color: #64748b;
    font-size: 11px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  .summary-box {{
    border: 1px solid #d8e0e7;
    background: var(--panel);
    padding: 14px;
    font-size: 14px;
    line-height: 1.55;
  }}
  .rank-list {{
    margin-top: 14px;
    border: 1px solid #d8e0e7;
  }}
  .rank-row {{
    display: grid;
    grid-template-columns: 36px 1fr auto;
    gap: 8px;
    padding: 8px 10px;
    border-top: 1px solid #edf2f7;
    font-size: 13px;
  }}
  .rank-row:first-child {{ border-top: 0; }}
  .rank-row button {{
    border: 0;
    background: transparent;
    color: var(--blue);
    text-align: left;
    padding: 0;
    cursor: pointer;
    font: inherit;
  }}
  .num {{ font-variant-numeric: tabular-nums; }}
  @media (max-width: 860px) {{
    header {{ align-items: flex-start; flex-direction: column; }}
    .metrics, .detail-grid {{ grid-template-columns: 1fr; }}
    .panel-head {{ grid-template-columns: 1fr; }}
    .r-badge {{ text-align: left; }}
  }}
</style>
</head>
<body>
<div class="shell">
  <header>
    <div>
      <h1>RTLDI ATLAS {atlas_year} Interactive Map</h1>
      <div class="subhead">Click a country to load its national data, capital exclusions, and nine-lever breakdown below the map.</div>
    </div>
    <div class="actions">
      <a class="button" href="../html-atlas/index.html">HTML Atlas</a>
      <a class="button primary" href="../atlas/RTLDI_ATLAS_2026_ebook.pdf">Print PDF</a>
    </div>
  </header>
  <main>
    <div class="map-frame">{plot_html}</div>
    <div class="hint"><span>Hover for quick metrics. Click for the full national explorer panel.</span><span id="selection-hint">No country selected</span></div>
    <section id="country-panel" aria-live="polite">
      <div class="empty">Select a country on the map to inspect its national RTLDI profile.</div>
    </section>
  </main>
</div>
<script>
const COUNTRY_DATA = {countries_json};

function money(value) {{
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  const n = Number(value);
  if (Math.abs(n) >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
  if (Math.abs(n) >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B';
  if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
  return '$' + Math.round(n).toLocaleString();
}}
function dollars(value) {{
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return '$' + Math.round(Number(value)).toLocaleString();
}}
function pop(value) {{
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  const n = Number(value);
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return Math.round(n / 1e3).toLocaleString() + 'k';
  return Math.round(n).toLocaleString();
}}
function pct(value) {{
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return (Number(value) * 100).toFixed(0) + '%';
}}
function rawValue(value) {{
  if (value === null || value === undefined || value === '') return 'N/A';
  return String(value);
}}
function escapeHtml(value) {{
  return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
}}
function strongestMissing(country) {{
  const missing = (country.components || []).filter(c => !c.bin);
  if (!missing.length) return 'All nine levers are currently marked present in the source data.';
  return 'Missing levers: ' + missing.map(c => c.num + '. ' + c.name).join('; ') + '.';
}}
function topLostCountries(region, selectedIso) {{
  return Object.values(COUNTRY_DATA)
    .filter(c => c.region === region && c.total_deficit_usd !== null && c.total_deficit_usd !== undefined)
    .sort((a, b) => Number(b.total_deficit_usd || 0) - Number(a.total_deficit_usd || 0))
    .slice(0, 8)
    .map((c, idx) => `<div class="rank-row">
      <span class="num">${{idx + 1}}</span>
      <button type="button" data-iso="${{escapeHtml(c.iso3)}}">${{escapeHtml(c.country)}}${{c.iso3 === selectedIso ? ' (selected)' : ''}}</button>
      <span class="num">${{money(c.total_deficit_usd)}}</span>
    </div>`).join('');
}}
function renderCountry(iso3) {{
  const country = COUNTRY_DATA[iso3];
  const panel = document.getElementById('country-panel');
  if (!country) {{
    panel.innerHTML = '<div class="empty">No national data is available for this map selection.</div>';
    return;
  }}
  document.getElementById('selection-hint').textContent = `${{country.country}} (${{country.iso3}})`;
  const yesCount = (country.components || []).filter(c => c.bin).length;
  const components = (country.components || []).map(c => `
    <div class="component">
      <div class="component-top">
        <strong>${{escapeHtml(c.num)}}. ${{escapeHtml(c.name)}}</strong>
        <span class="status ${{c.bin ? 'yes' : 'no'}}">${{c.bin ? 'Yes' : 'No'}}</span>
      </div>
      <div class="component-desc">${{escapeHtml(c.desc || '')}}</div>
      <div class="raw">raw: ${{escapeHtml(rawValue(c.raw))}} | threshold: ${{escapeHtml(rawValue(c.thresh))}}</div>
    </div>`).join('');

  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <h2 class="panel-title">${{escapeHtml(country.country)}} (${{escapeHtml(country.iso3)}})</h2>
        <div class="panel-meta">${{escapeHtml(country.region)}} | V-Dem ${{escapeHtml(country.vdem_year)}} | GDP baseline ${{escapeHtml(country.g0_year)}} | ${{yesCount}}/9 levers present</div>
      </div>
      <div class="r-badge"><span>R score</span><strong>${{country.r === null ? 'N/A' : Number(country.r).toFixed(2)}}</strong></div>
    </div>
    <div class="metrics">
      <div class="metric"><label>Annual capital exclusions</label><strong>${{money(country.total_deficit_usd)}}</strong></div>
      <div class="metric"><label>Capital exclusions / cap</label><strong>${{dollars(country.delta_g_per_capita)}}</strong></div>
      <div class="metric"><label>GDP per capita G0</label><strong>${{dollars(country.g0)}}</strong></div>
      <div class="metric"><label>Population</label><strong>${{pop(country.population)}}</strong></div>
    </div>
    <div class="detail-grid">
      <div>
        <div class="section-label">Nine-lever breakdown</div>
        <div class="components">${{components || '<div class="empty">No component breakdown available.</div>'}}</div>
      </div>
      <aside>
        <div class="section-label">Interpretive summary</div>
        <div class="summary-box">
          <strong>${{escapeHtml(country.country)}}</strong> has an R score of ${{country.r === null ? 'N/A' : Number(country.r).toFixed(2)}} (${{yesCount}}/9 levers present).
          Its annual capital exclusions are estimated at <strong>${{money(country.total_deficit_usd)}}</strong>, or <strong>${{dollars(country.delta_g_per_capita)}}</strong> per person under the current atlas rule.
          <br><br>${{escapeHtml(strongestMissing(country))}}
        </div>
        <div class="section-label" style="margin-top:16px;">Largest capital exclusions in ${{escapeHtml(country.region)}}</div>
        <div class="rank-list">${{topLostCountries(country.region, country.iso3)}}</div>
      </aside>
    </div>`;

  panel.querySelectorAll('button[data-iso]').forEach(button => {{
    button.addEventListener('click', () => renderCountry(button.dataset.iso));
  }});
  panel.scrollIntoView({{behavior: 'smooth', block: 'start'}});
}}
function bindMapClicks() {{
  const graph = document.getElementById('rtldi-map');
  if (!graph || !graph.on) {{
    window.setTimeout(bindMapClicks, 100);
    return;
  }}
  graph.on('plotly_click', event => {{
    const point = event && event.points && event.points[0];
    if (point && point.location) renderCountry(point.location);
  }});
}}
document.addEventListener('DOMContentLoaded', bindMapClicks);
</script>
</body>
</html>
"""


def safe_write_image(fig, path: Path, **kwargs) -> None:
    try:
        fig.write_image(path, **kwargs)
        print(f"Saved {path.suffix.upper().lstrip('.')}: {path}  ({path.stat().st_size / 1024:.0f} KB)")
    except Exception as exc:
        if path.exists():
            print(f"Reused existing {path.name}; static export failed: {str(exc).splitlines()[0]}")
            return
        raise


def main():
    parser = argparse.ArgumentParser(description="Generate enclosure strength choropleth from RTLDI ATLAS data.")
    parser.add_argument("--year", type=int, default=2026, help="Atlas year label (default 2026)")
    parser.add_argument(
        "--input",
        default=None,
        help=f"Path to rtl_di_atlas_un_members_*.csv (default: {DEFAULT_ATLAS_CSV})",
    )
    parser.add_argument(
        "--out-dir", default=str(OUT_DIR), help="Directory for map outputs (default outputs/figures)"
    )
    args = parser.parse_args()

    df = load_atlas_for_map(args.input)

    # Sanity
    n = len(df)
    r_min, r_max = float(df["r"].min()), float(df["r"].max())
    print(f"Countries with R: {n} | R range: [{r_min:.3f}, {r_max:.3f}]")
    if n < 190:
        print("WARNING: fewer than ~193 rows — some countries may be missing iso3 or r values.")

    fig = make_choropleth(df, atlas_year=args.year)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"rtl_di_enclosure_strength_{args.year}_choropleth"

    # Interactive explorer: hover shows quick metrics; click loads national detail below the map.
    html_path = out_dir / f"{stem}.html"
    html_path.write_text(build_interactive_html(fig, df, atlas_year=args.year), encoding="utf-8")
    print(f"Saved interactive: {html_path}")

    # Static PNG (high-res for print, reports, ebook embedding)
    png_path = out_dir / f"{stem}.png"
    safe_write_image(fig, png_path, width=1380, height=820, scale=2)

    # Vector PDF (high-quality for print docs, reports, and embedding)
    pdf_path = out_dir / f"{stem}.pdf"
    safe_write_image(fig, pdf_path, width=1380, height=820)

    print("\nDone. Enclosure strength = RTLP R (higher = stronger protection allowing capital to operate without exclusion).")
    print("To re-run with fresh data: python -m src.build_atlas --year 2026 && python -m src.generate_enclosure_map")


if __name__ == "__main__":
    main()
