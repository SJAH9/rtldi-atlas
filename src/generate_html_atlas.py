#!/usr/bin/env python3
"""
Generate a totally self-contained HTML atlas (outputs/html-atlas/) containing
the same data as the print atlas front matter + 22 regional summaries.

- Reuses prepare_atlas_data() so numbers, caps, 9-indicator breakdowns, region
  aggregates, and member lists are identical to the PDF.
- Vector choropleth maps (SVG) for global + all 22 regions using the same
  plotly code path (Mollweide-inspired or standard geo, Viridis R scale).
- Single index.html with embedded data (JSON) + Tailwind via CDN (common
  pattern for rich self-contained data apps) + vanilla JS for all interactivity:
  live sortable/filterable/searchable nation table, region explorer that
  swaps vector map + stats + 9-lever breakdown + best/worst + member list,
  dynamic bars, etc.
- No server required. Open index.html in any modern browser. All maps are
  local vector SVGs in the maps/ subdirectory.

Run:
  python -m src.generate_html_atlas

Outputs:
  outputs/html-atlas/index.html
  outputs/html-atlas/maps/*.svg   (global + 22 regional vector choropleths)
  (Optional: also copies the interactive global .html and high-res PNGs for reference)
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

try:
    import plotly.express as px
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# Reuse the exact data prep (capped deltas, regional aggregates, global 9-ind losses, etc.)
# This guarantees the HTML and the print PDF are derived from identical numbers.
from src.generate_atlas_ebook import prepare_atlas_data, ETA

# Consistent with the PDF (Viridis, same R encoding)
R_SCALE = [[0.0, "#440154"], [0.25, "#3b528b"], [0.5, "#21918c"], [0.75, "#5ec962"], [1.0, "#fde725"]]
LOW_R = 0.35
HIGH_R = 0.65

HTML_DIR = Path("outputs/html-atlas")
MAPS_DIR = HTML_DIR / "maps"

# Clean lever short names (from the launch-polished first-principles descriptions)
LEVER_SHORT = {
    1: "Legal Protections",
    2: "Independent Judiciary",
    3: "Law Enforcement Accountability",
    4: "Protection Against Arbitrary Detention",
    5: "Freedom from Torture & Inhumane Treatment",
    6: "Civilian Protection in Conflict",
    7: "Access to Justice",
    8: "Freedom of Expression & Whistleblowers",
    9: "Socioeconomic Conditions (Food/Health/Shelter)",
}

def format_usd(n: float) -> str:
    if n >= 1e12:
        return f"${n/1e12:,.2f}T"
    if n >= 1e9:
        return f"${n/1e9:,.1f}B"
    if n >= 1e6:
        return f"${n/1e6:,.1f}M"
    return f"${n:,.0f}"

def format_pop(n: float) -> str:
    if n >= 1e9:
        return f"{n/1e9:.2f}B"
    if n >= 1e6:
        return f"{n/1e6:.1f}M"
    if n >= 1e3:
        return f"{n/1e3:.0f}k"
    return f"{int(n):,}"

def slugify(s: str) -> str:
    return s.lower().replace(" ", "_").replace("/", "_").replace(",", "").replace("&", "and")

def get_global_svg(df: pd.DataFrame, out_path: Path) -> Path:
    """Global choropleth SVG (vector, same aesthetic as print)."""
    if not HAS_PLOTLY:
        return out_path
    fig = px.choropleth(
        df,
        locations="iso3",
        color="r",
        locationmode="ISO-3",
        color_continuous_scale="Viridis",
        range_color=(0, 1),
        hover_name="country",
        hover_data={
            "r": ":.2f",
            "total_deficit_usd": ":.0f",
            "delta_g_per_capita": ":.0f",
        },
        title="Enclosure Strength (R) — Global",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        coloraxis_colorbar=dict(title="R (0–1)", len=0.6),
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="rgba(0,0,0,0.2)",
        showland=True,
        landcolor="rgba(240,240,240,0.6)",
        showocean=True,
        oceancolor="rgba(230,240,250,0.4)",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(out_path), format="svg", width=1200, height=620)
    return out_path

def get_regional_svg(region_name: str, members: List[dict], all_df: pd.DataFrame, out_path: Path) -> Path:
    """Regional choropleth SVG focused on the countries in the region (fitbounds)."""
    if not HAS_PLOTLY or not members:
        return out_path
    isos = [m["iso3"] for m in members]
    focus_df = all_df[all_df["iso3"].isin(isos)].copy()
    if focus_df.empty:
        return out_path

    fig = px.choropleth(
        focus_df,
        locations="iso3",
        color="r",
        locationmode="ISO-3",
        color_continuous_scale="Viridis",
        range_color=(0, 1),
        hover_name="country",
        hover_data={"r": ":.2f", "total_deficit_usd": ":.0f"},
        title=f"{region_name} — Enclosure Strength (R)",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=25, b=0),
        coloraxis_colorbar=dict(title="R", len=0.5),
    )
    fig.update_geos(fitbounds="locations", visible=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(out_path), format="svg", width=900, height=520)
    return out_path

def build_html_atlas(data: Dict[str, Any]) -> Path:
    """Main builder. Produces the self-contained HTML directory + vector SVGs."""
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Data we will embed (exact same as PDF front + regions) ---
    regional_data: Dict[str, Any] = data["regional_data"]
    sorted_regions: List[tuple] = data["sorted_regions"]
    global_total_lost: float = data["global_total_lost"]
    global_indicator_losts: List[float] = data["global_indicator_losts"]
    indicator_names: List[str] = data["indicator_names"]
    indicator_descs: List[str] = data["indicator_descs"]
    detailed_by_loss: List[Dict] = data["detailed_by_loss"]

    # Master table rows (for the interactive summary table)
    nations = []
    for d in detailed_by_loss:
        nations.append({
            "iso3": d["iso3"],
            "country": d.get("country", d["iso3"]),
            "region": d.get("un_region", ""),
            "r": round(float(d.get("r", 0)), 4),
            "g0": round(float(d.get("g0", 0)), 2),
            "pop": float(d.get("population", 0)),
            "lost_per_cap": round(float(d.get("delta_g_per_capita", 0)), 2),
            "total_lost": float(d.get("total_deficit_usd", 0)),
            "rank": d.get("rank_by_total_deficit"),
        })

    # Pre-compute region detail packets (same logic as PDF for paras, best/worst, indicators)
    region_packets = {}
    for reg_name, reg_sum in regional_data.items():
        members = reg_sum.get("members", [])
        n = reg_sum["n_countries"]
        best = worst = None
        if n > 3 and members:
            valid = [m for m in members if m.get("r") is not None]
            if valid:
                best = max(valid, key=lambda x: x["r"])
                worst = min(valid, key=lambda x: x["r"])

        inds = reg_sum.get("indicators", [])
        para1 = para2 = ""
        if inds:
            sorted_inds = sorted(inds, key=lambda x: x.get("frac_yes", 0), reverse=True)
            strong_names = [i["name"].split(" (")[0][:40] for i in sorted_inds[:2] if i.get("frac_yes", 0) > 0.4]
            weak_names = [i["name"].split(" (")[0][:40] for i in sorted_inds[-2:]]
            potential_b = sum(i.get("attributable_lost_gdp", 0) for i in sorted_inds[-3:]) / 1e9
            para1 = (
                f"The {reg_name} region has a population-weighted average RTLP score of {reg_sum['weighted_r']:.2f}. "
                f"Across its {n} member countries, roughly {reg_sum['weighted_r']*100:.0f}% of the nine core protections are in place on average, "
                f"resulting in an estimated ${reg_sum['total_lost_gdp']/1e9:,.1f} billion in annual lost GDP. "
                f"The region shows strength in {', '.join(strong_names) if strong_names else 'key areas'}."
            )
            if best and worst:
                para1 += f" Highest: {best.get('country', best.get('iso3'))} (R={best['r']:.2f}). Lowest: {worst.get('country', worst.get('iso3'))} (R={worst['r']:.2f})."
            para2 = (
                f"Weaker indicators (especially {', '.join(weak_names) if weak_names else 'priority areas'}) "
                f"are linked to the largest slices of the region's bounded disparity. "
                f"Improvement on the weakest three is cross-sectionally associated with up to ${potential_b:,.1f} billion in reduced annual loss (within the 25% cap)."
            )

        # Pre-format indicators for the region (same numbers as PDF)
        region_inds = []
        for i in inds:
            region_inds.append({
                "num": i["num"],
                "name": LEVER_SHORT.get(i["num"], i.get("name", "")),
                "frac_yes": round(i.get("frac_yes", 0), 3),
                "n_yes": i.get("n_yes", 0),
                "attributable": i.get("attributable_lost_gdp", 0),
            })

        region_packets[reg_name] = {
            "name": reg_name,
            "slug": slugify(reg_name),
            "n": n,
            "total_pop": reg_sum["total_pop"],
            "weighted_r": round(reg_sum["weighted_r"], 4),
            "mean_r": round(reg_sum["mean_r"], 4),
            "total_lost": reg_sum["total_lost_gdp"],
            "best": {"name": best.get("country", "") if best else "", "r": round(best["r"], 2)} if best else None,
            "worst": {"name": worst.get("country", "") if worst else "", "r": round(worst["r"], 2)} if worst else None,
            "indicators": region_inds,
            "para1": para1,
            "para2": para2,
            "members": [{"iso3": m["iso3"], "country": m.get("country", m["iso3"]), "r": round(float(m.get("r", 0)), 3), "lost": float(m.get("total_deficit_usd", 0))} for m in members],
        }

    # --- Generate vector SVG maps (global + 22 regions) ---
    print("Generating vector choropleth SVGs for HTML atlas...")
    master_df = pd.DataFrame([{
        "iso3": d["iso3"],
        "country": d.get("country", d["iso3"]),
        "un_region": d.get("un_region", ""),
        "r": d.get("r", 0),
        "total_deficit_usd": d.get("total_deficit_usd", 0),
        "delta_g_per_capita": d.get("delta_g_per_capita", 0),
    } for d in detailed_by_loss])

    # Global
    global_svg = MAPS_DIR / "global.svg"
    get_global_svg(master_df, global_svg)

    # Regional SVGs
    for reg_name, reg_sum in regional_data.items():
        slug = slugify(reg_name)
        svg_path = MAPS_DIR / f"{slug}.svg"
        get_regional_svg(reg_name, reg_sum.get("members", []), master_df, svg_path)

    # Also copy useful reference assets (interactive global + original PNGs) if present
    ref_global = Path("outputs/figures/rtl_di_enclosure_strength_2026_choropleth.html")
    if ref_global.exists():
        shutil.copy(ref_global, HTML_DIR / "global_interactive.html")

    png_src = Path("outputs/figures/regional_choropleths")
    if png_src.exists():
        for p in png_src.glob("*.png"):
            shutil.copy(p, MAPS_DIR / p.name)

    # --- Build the single index.html ---
    # Embed compact data
    embed_nations = nations
    embed_regions = {k: v for k, v in region_packets.items()}
    embed_global = {
        "total_lost": global_total_lost,
        "indicator_losts": global_indicator_losts,
        "indicator_names": indicator_names,
        "indicator_descs": indicator_descs,
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RTLDI ATLAS 2026 — HTML (Front + Regions)</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
  :root {{ --font-sans: Inter, system-ui, sans-serif; }}
  body {{ font-family: var(--font-sans); }}
  .heading {{ font-family: 'Space Grotesk', Inter, system-ui, sans-serif; font-weight: 600; letter-spacing: -.02em; }}
  .stat {{ font-variant-numeric: tabular-nums; }}
  .data-table th {{ position: sticky; top: 0; background: #fff; z-index: 10; }}
  .r-high {{ background-color: #ecfdf5; color: #065f46; }}
  .r-mid  {{ background-color: #fefce8; color: #713f12; }}
  .r-low  {{ background-color: #fef2f2; color: #991b1b; }}
  .lever-bar {{ height: 10px; background: linear-gradient(to right, #64748b, #0ea47a); border-radius: 9999px; transition: width .4s ease; }}
  .map-container svg, .map-container img {{ max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 3px rgb(0 0 0 / 0.05); }}
  .section-title {{ font-size: 1.05rem; letter-spacing: -.015em; }}
</style>
</head>
<body class="bg-slate-50 text-slate-900">
<div class="max-w-screen-xl mx-auto">
  <!-- Header -->
  <header class="border-b border-slate-200 bg-white sticky top-0 z-50">
    <div class="px-6 py-4 flex items-center justify-between">
      <div>
        <div class="flex items-center gap-x-3">
          <div class="w-9 h-9 bg-emerald-600 rounded-xl flex items-center justify-center text-white text-xl font-semibold">R</div>
          <div>
            <span class="heading text-2xl font-semibold tracking-tighter">RTLDI ATLAS 2026</span>
            <span class="ml-2 text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full font-medium">HTML EDITION</span>
          </div>
        </div>
        <div class="text-[11px] text-slate-500 mt-0.5">Front Matter + 22 Regional Summaries • Same data as the print atlas • Self-contained</div>
      </div>
      <div class="flex items-center gap-x-2 text-sm">
        <a href="../atlas/RTLDI_ATLAS_2026_ebook.pdf" class="px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">Download Print PDF</a>
        <a href="global_interactive.html" target="_blank" class="px-3 py-1.5 rounded-xl bg-slate-900 text-white hover:bg-black transition">Global Interactive Map</a>
        <span class="text-[10px] text-slate-400">V-Dem 2024 + WB 2026 G₀</span>
      </div>
    </div>
  </header>

  <!-- Hero / Global Snapshot -->
  <div class="px-6 pt-8 pb-6">
    <div class="max-w-3xl">
      <h1 class="heading text-5xl tracking-tighter font-semibold">Right-to-Life Deficit Index</h1>
      <p class="mt-3 text-xl text-slate-600">Annual GDP disparity associated with nine binary protections of life and dignity. The data is identical to the print atlas front matter and regional pages.</p>
    </div>

    <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-500">Global Annual Lost GDP (capped)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat">{format_usd(global_total_lost)}</div>
        <div class="text-emerald-600 text-sm mt-1">Every year, recurring</div>
      </div>
      <div class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-500">Population-weighted Enclosure Strength (R)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat">{data.get('weighted_r', 0.21):.2f}</div>
        <div class="text-sm mt-1">0 = no protections • 1 = full set of 9</div>
      </div>
      <div class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-500">UN Member States</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat">193</div>
        <div class="text-sm mt-1">22 UN regions</div>
      </div>
      <div class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-500">Conservative Marginal Coefficient (η)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat">0.30</div>
        <div class="text-sm mt-1">25% institutional cap applied (raw data suggested ~0.33)</div>
      </div>
    </div>
  </div>

  <!-- Nested Causal Modelling / 9 Levers (condensed, same as print front) -->
  <div class="px-6 pb-8">
    <div class="bg-white border border-slate-100 rounded-3xl p-6">
      <div class="uppercase text-xs tracking-[1px] text-emerald-700 font-semibold mb-2">Nested Causal Modelling / Mapping</div>
      <div class="prose prose-slate max-w-none text-[14.5px] leading-snug">
        <p>The nine levers were identified by nested causal modelling of global data with the explicit target of maximal GDP. Each lever is a simple binary condition — present or absent. When present, it acts as a low-cost force multiplier for economic velocity. The 25% cap is a deliberate limiter on projection volatility.</p>
        <p class="mt-3">Whistleblower example: most levers carry low annual cost. For Freedom of Expression &amp; Whistleblower Protections, one must simply make their protection the law and listen for the whistles to blow and tell you where the corruption is in your government.</p>
      </div>
      <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
        {"".join([f'<div class="px-3 py-2 rounded-2xl bg-slate-50 border border-slate-100"><span class="font-medium">{LEVER_SHORT.get(i, n)}</span></div>' for i, n in enumerate(indicator_names[:9], 1)])}
      </div>
    </div>
  </div>

  <!-- Global 9-Indicator Lost GDP Breakdown (front-matter carto data) -->
  <div class="px-6 pb-8">
    <div class="flex items-baseline justify-between mb-3">
      <div class="section-title font-semibold">Global Lost GDP by Missing Lever</div>
      <div class="text-xs text-slate-500">Attributable share of the {format_usd(global_total_lost)} total (capped)</div>
    </div>
    <div id="global-bars" class="grid grid-cols-1 md:grid-cols-3 gap-3"></div>
  </div>

  <!-- Interactive Nation Summary Table (exact same data as print front-matter table) -->
  <div class="px-6 pb-10">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title font-semibold">All 193 UN Member States — Summary (sorted by total lost GDP)</div>
      <div class="text-xs text-slate-500">Live client-side filtering &amp; sorting • Same numbers as the print atlas</div>
    </div>

    <div class="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
      <div class="p-3 border-b flex flex-wrap gap-2 items-center bg-slate-50">
        <input id="search" type="text" placeholder="Search country or ISO..." class="flex-1 min-w-[180px] px-3 py-1.5 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:border-emerald-300">
        <select id="region-filter" class="px-3 py-1.5 text-sm border border-slate-200 rounded-2xl bg-white">
          <option value="">All regions</option>
        </select>
        <button onclick="resetFilters()" class="px-3 py-1 text-xs rounded-2xl border border-slate-200 hover:bg-white">Reset</button>
      </div>
      <div class="overflow-auto max-h-[520px]">
        <table id="nations-table" class="w-full text-sm">
          <thead class="text-xs uppercase text-slate-500 border-b">
            <tr>
              <th class="px-3 py-2 text-left w-8 cursor-pointer" data-sort="rank">#</th>
              <th class="px-3 py-2 text-left cursor-pointer" data-sort="country">Country</th>
              <th class="px-3 py-2 text-left cursor-pointer" data-sort="region">Region</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="r">R</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="g0">G₀ (USD)</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="pop">Pop</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="lost_per_cap">Lost / cap</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="total_lost">Total Lost (USD)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-[13px]"></tbody>
        </table>
      </div>
      <div class="px-3 py-2 text-[10px] text-slate-400 border-t bg-slate-50">R color: &lt;{LOW_R} red tint • {LOW_R}–{HIGH_R} yellow • &gt;{HIGH_R} green tint. Numbers use the same 25% contextual cap as the print edition.</div>
    </div>
  </div>

  <!-- Regional Explorer -->
  <div class="px-6 pb-12">
    <div class="section-title font-semibold mb-3">Regional Summaries (identical to print regions.pdf)</div>

    <!-- Region cards -->
    <div id="region-cards" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-2 mb-6"></div>

    <!-- Detail pane -->
    <div id="region-detail" class="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm hidden">
      <div class="flex items-start gap-4">
        <div class="flex-1">
          <div class="flex items-center gap-x-3">
            <div id="detail-name" class="text-2xl font-semibold heading"></div>
            <div id="detail-stats" class="text-sm text-slate-500"></div>
          </div>

          <div class="mt-3 grid grid-cols-1 lg:grid-cols-5 gap-4">
            <!-- Map -->
            <div class="lg:col-span-3 map-container" id="detail-map"></div>

            <!-- Stats + best/worst -->
            <div class="lg:col-span-2 space-y-3 text-sm">
              <div class="grid grid-cols-3 gap-2">
                <div class="rounded-2xl border border-slate-100 p-3">
                  <div class="text-[10px] text-slate-500">Weighted R</div>
                  <div id="detail-r" class="text-2xl font-semibold tabular-nums"></div>
                </div>
                <div class="rounded-2xl border border-slate-100 p-3">
                  <div class="text-[10px] text-slate-500">Total Lost GDP</div>
                  <div id="detail-lost" class="text-2xl font-semibold tabular-nums"></div>
                </div>
                <div class="rounded-2xl border border-slate-100 p-3">
                  <div class="text-[10px] text-slate-500">Countries / Pop</div>
                  <div id="detail-n-pop" class="text-xl font-medium tabular-nums"></div>
                </div>
              </div>

              <div id="detail-bestworst" class="text-xs leading-snug"></div>

              <div>
                <div class="text-[10px] uppercase tracking-widest text-slate-500 mb-1">9 Levers — Regional Breakdown</div>
                <div id="detail-indicators" class="text-xs space-y-1"></div>
                <div id="detail-universal" class="mt-2 text-[11px] font-medium text-red-700"></div>
              </div>
            </div>
          </div>

          <!-- Descriptions (same style as print) -->
          <div id="detail-desc" class="mt-4 text-sm text-slate-600 leading-snug prose prose-sm max-w-none"></div>

          <!-- Members -->
          <div class="mt-4">
            <div class="flex items-center justify-between text-[10px] uppercase tracking-widest text-slate-500 mb-1">
              <span>Member Nations (click to filter main table)</span>
            </div>
            <div id="detail-members" class="max-h-40 overflow-auto text-xs border border-slate-100 rounded-2xl p-2 bg-slate-50 grid grid-cols-2 md:grid-cols-3 gap-x-3 gap-y-0.5"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <footer class="px-6 pb-10 text-[10px] text-slate-400">
    Self-contained HTML atlas • Data &amp; methodology identical to RTLDI_ATLAS_2026_ebook.pdf (v2026.6) • Generated from the same 2026 rule (V-Dem 2024 + World Bank 2026 G₀) and 0.30 Conservative Marginal Coefficient with 25% cap.
    Vector maps are SVG exports from the identical plotly choropleth code used for the print edition (Mollweide / equal-area where possible).
  </footer>
</div>

<script>
// ================== EMBEDDED DATA (identical to print) ==================
const ATLAS = {{
  global: {json.dumps(embed_global, indent=0)},
  nations: {json.dumps(embed_nations, indent=0)},
  regions: {json.dumps(embed_regions, indent=0)}
}};

const LOW_R = {LOW_R};
const HIGH_R = {HIGH_R};

// Client-side helpers (executed in browser)
function formatPop(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'k';
  return Math.round(n).toLocaleString();
}

// Tailwind script run
function initTailwind() {{
  // Already loaded via CDN. Add any runtime theme if needed.
}}

// ================== GLOBAL 9-INDICATOR BARS (vector-ish via divs + labels) ==================
function renderGlobalBars() {{
  const container = document.getElementById('global-bars');
  container.innerHTML = '';
  const total = ATLAS.global.total_lost || 0;
  const names = ATLAS.global.indicator_names || [];
  const losts = ATLAS.global.indicator_losts || [];
  const maxLost = Math.max(...losts, 1);

  for (let i = 0; i < Math.min(9, names.length); i++) {{
    const name = names[i] || `Indicator ${{i+1}}`;
    const lost = losts[i] || 0;
    const pct = total > 0 ? (lost / total) * 100 : 0;
    const w = Math.max(4, (lost / maxLost) * 100);

    const el = document.createElement('div');
    el.className = 'bg-white border border-slate-100 rounded-2xl p-3 flex gap-3 items-center';
    el.innerHTML = `
      <div class="flex-1 min-w-0">
        <div class="flex justify-between text-xs">
          <div class="font-medium truncate pr-2">${{name}}</div>
          <div class="tabular-nums text-emerald-700 font-medium">${{(lost/1e9).toFixed(1)}}B</div>
        </div>
        <div class="mt-1.5 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-2 bg-gradient-to-r from-emerald-600 to-teal-500" style="width:${{w}}%"></div>
        </div>
      </div>
      <div class="text-[10px] text-slate-400 w-9 text-right tabular-nums">${{pct.toFixed(0)}}%</div>
    `;
    container.appendChild(el);
  }}
}}

// ================== NATIONS TABLE (fully interactive in HTML/JS) ==================
let currentSort = {{ key: 'total_lost', dir: 'desc' }};
let currentFilter = {{ search: '', region: '' }};

function getRClass(r) {{
  if (r >= HIGH_R) return 'r-high';
  if (r >= LOW_R) return 'r-mid';
  return 'r-low';
}}

function renderNationsTable(filtered) {{
  const tbody = document.querySelector('#nations-table tbody');
  tbody.innerHTML = '';

  const rows = filtered || ATLAS.nations;

  rows.forEach((n, idx) => {{
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 ' + getRClass(n.r);
    const popStr = n.pop >= 1e9 ? (n.pop/1e9).toFixed(2)+'B' : n.pop >= 1e6 ? (n.pop/1e6).toFixed(1)+'M' : (n.pop/1e3).toFixed(0)+'k';
    tr.innerHTML = `
      <td class="px-3 py-1.5 font-mono text-[11px] text-slate-400">${{n.rank || (idx+1)}}</td>
      <td class="px-3 py-1.5 font-medium">${{n.country}}</td>
      <td class="px-3 py-1.5 text-xs text-slate-500">${{n.region}}</td>
      <td class="px-3 py-1.5 text-right font-medium tabular-nums">${{n.r.toFixed(2)}}</td>
      <td class="px-3 py-1.5 text-right tabular-nums">${{Math.round(n.g0).toLocaleString()}}</td>
      <td class="px-3 py-1.5 text-right text-xs tabular-nums">${{popStr}}</td>
      <td class="px-3 py-1.5 text-right tabular-nums">${{n.lost_per_cap.toLocaleString()}}</td>
      <td class="px-3 py-1.5 text-right font-medium tabular-nums">${{(n.total_lost/1e9).toFixed(1)}}B</td>
    `;
    tr.onclick = () => filterTableByRegion(n.region);
    tbody.appendChild(tr);
  }});
}}

function applyFilters() {{
  let rows = [...ATLAS.nations];
  const q = currentFilter.search.toLowerCase();
  if (q) {{
    rows = rows.filter(n => n.country.toLowerCase().includes(q) || n.iso3.toLowerCase().includes(q));
  }}
  if (currentFilter.region) {{
    rows = rows.filter(n => n.region === currentFilter.region);
  }}
  // sort
  const k = currentSort.key;
  rows.sort((a, b) => {{
    let va = a[k], vb = b[k];
    if (k === 'country' || k === 'region') {{
      va = (va || '').toString().toLowerCase();
      vb = (vb || '').toString().toLowerCase();
      return currentSort.dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    }}
    return currentSort.dir === 'asc' ? (va - vb) : (vb - va);
  }});
  renderNationsTable(rows);
}}

function resetFilters() {{
  currentFilter = {{ search: '', region: '' }};
  document.getElementById('search').value = '';
  document.getElementById('region-filter').value = '';
  applyFilters();
}}

function filterTableByRegion(region) {{
  currentFilter.region = region;
  document.getElementById('region-filter').value = region;
  applyFilters();
  // scroll to table
  document.querySelector('#nations-table').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}}

function initNationTable() {{
  // populate region filter
  const sel = document.getElementById('region-filter');
  const regs = [...new Set(ATLAS.nations.map(n => n.region))].sort();
  regs.forEach(r => {{
    if (!r) return;
    const o = document.createElement('option');
    o.value = r; o.textContent = r;
    sel.appendChild(o);
  }});

  sel.onchange = () => {{
    currentFilter.region = sel.value;
    applyFilters();
  }};

  const search = document.getElementById('search');
  search.oninput = () => {{
    currentFilter.search = search.value;
    applyFilters();
  }};

  // column sorting
  document.querySelectorAll('#nations-table th[data-sort]').forEach(th => {{
    th.onclick = () => {{
      const key = th.dataset.sort;
      if (currentSort.key === key) {{
        currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
      }} else {{
        currentSort = {{ key, dir: key === 'total_lost' || key === 'rank' ? 'desc' : 'asc' }};
      }}
      applyFilters();
    }});
  }});

  renderNationsTable(ATLAS.nations);
}}

// ================== REGION EXPLORER (maps are local SVGs, everything else JS) ==================
let currentRegion = null;

function renderRegionCards() {{
  const container = document.getElementById('region-cards');
  container.innerHTML = '';
  const sorted = Object.values(ATLAS.regions).sort((a,b) => b.total_lost - a.total_lost);

  sorted.forEach(reg => {{
    const card = document.createElement('div');
    card.className = 'cursor-pointer bg-white border border-slate-200 hover:border-emerald-300 transition rounded-2xl p-3 text-xs shadow-sm';
    card.innerHTML = `
      <div class="font-semibold truncate">${{reg.name}}</div>
      <div class="mt-1 flex justify-between items-baseline">
        <div class="tabular-nums font-medium">${{(reg.total_lost/1e9).toFixed(1)}}B</div>
        <div class="text-emerald-700 font-medium">R ${{reg.weighted_r.toFixed(2)}}</div>
      </div>
      <div class="text-[10px] text-slate-500">${{reg.n}} countries</div>
    `;
    card.onclick = () => showRegionDetail(reg.name);
    container.appendChild(card);
  }});
}}

function showRegionDetail(regName) {{
  const reg = ATLAS.regions[regName];
  if (!reg) return;
  currentRegion = regName;

  const detail = document.getElementById('region-detail');
  detail.classList.remove('hidden');
  detail.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});

  document.getElementById('detail-name').textContent = reg.name;
  document.getElementById('detail-stats').innerHTML = `${{reg.n}} countries • ${{formatPop(reg.total_pop)}}`;

  // Map (vector SVG)
  const mapEl = document.getElementById('detail-map');
  const svgSrc = `maps/${{reg.slug}}.svg`;
  mapEl.innerHTML = `<img src="${{svgSrc}}" alt="${{reg.name}} choropleth (vector)" class="w-full">`;

  document.getElementById('detail-r').textContent = reg.weighted_r.toFixed(2);
  document.getElementById('detail-lost').innerHTML = `<span class="text-base align-super">$</span>${{(reg.total_lost/1e9).toFixed(1)}}<span class="text-base align-super">B</span>`;
  document.getElementById('detail-n-pop').textContent = `${{reg.n}} / ${{formatPop(reg.total_pop)}}`;

  // Best / worst
  const bw = document.getElementById('detail-bestworst');
  bw.innerHTML = '';
  if (reg.best && reg.worst) {{
    bw.innerHTML = `<span class="font-medium">Best:</span> ${{reg.best.name}} (R=${{reg.best.r}}) &nbsp;•&nbsp; <span class="font-medium">Worst:</span> ${{reg.worst.name}} (R=${{reg.worst.r}})`;
  }}

  // 9 indicators
  const indContainer = document.getElementById('detail-indicators');
  indContainer.innerHTML = '';
  let weakest = null;
  reg.indicators.forEach(ind => {{
    const row = document.createElement('div');
    row.className = 'flex items-center gap-2';
    const pct = (ind.frac_yes * 100).toFixed(0);
    const lostB = (ind.attributable / 1e9).toFixed(1);
    row.innerHTML = `
      <div class="w-4 text-right font-mono text-[10px] text-slate-400">${{ind.num}}</div>
      <div class="flex-1 truncate">${{ind.name}}</div>
      <div class="w-8 text-right tabular-nums">${{pct}}%</div>
      <div class="w-14 text-right tabular-nums text-emerald-700">${{lostB}}B</div>
    `;
    indContainer.appendChild(row);
    if (!weakest || ind.frac_yes < weakest.frac_yes) weakest = ind;
  }});

  // Universal fail callout (same spirit as print)
  const univ = document.getElementById('detail-universal');
  if (weakest && weakest.frac_yes < 0.35) {{
    univ.textContent = `Universal-failing lever in region: ${{weakest.name}} (only ${{ (weakest.frac_yes*100).toFixed(0) }}% of countries have it)`;
  }} else {{
    univ.textContent = '';
  }}

  // Descriptions
  document.getElementById('detail-desc').innerHTML = `
    <p>${{reg.para1}}</p>
    ${{reg.para2 ? `<p class="mt-2">${{reg.para2}}</p>` : ''}}
  `;

  // Members (clickable)
  const memEl = document.getElementById('detail-members');
  memEl.innerHTML = '';
  const sortedMembers = [...reg.members].sort((a,b) => b.lost - a.lost).slice(0, 18);
  sortedMembers.forEach(m => {{
    const pill = document.createElement('div');
    pill.className = 'px-1.5 py-0.5 rounded hover:bg-white cursor-pointer flex justify-between';
    pill.innerHTML = `<span class="truncate">${{m.country}}</span><span class="font-mono text-emerald-700 ml-1">${{(m.lost/1e9).toFixed(1)}}B</span>`;
    pill.onclick = () => filterTableByRegion(reg.name);
    memEl.appendChild(pill);
  }});
  if (reg.members.length > 18) {{
    const more = document.createElement('div');
    more.className = 'col-span-full text-[10px] text-slate-400 mt-0.5';
    more.textContent = `+${{reg.members.length - 18}} more — filter the main table to see all`;
    memEl.appendChild(more);
  }}
}}

function initRegionExplorer() {{
  renderRegionCards();
  // Auto-select the highest-loss region on load
  const first = Object.values(ATLAS.regions).sort((a,b)=>b.total_lost-a.total_lost)[0];
  if (first) {{
    // small delay so cards are visible
    setTimeout(() => showRegionDetail(first.name), 120);
  }}
}}

// ================== BOOT ==================
function boot() {{
  initTailwind();
  renderGlobalBars();
  initNationTable();
  initRegionExplorer();

  // Keyboard niceties
  document.addEventListener('keydown', e => {{
    if (e.key === '/' && document.activeElement.tagName === 'BODY') {{
      e.preventDefault();
      document.getElementById('search').focus();
    }}
  }});

  // Initial table render already done in initNationTable
  console.log('%c[RTLDI HTML Atlas] Self-contained front+regions ready. Data matches print atlas.', 'color:#166534');
}}

window.resetFilters = resetFilters;
document.addEventListener('DOMContentLoaded', boot);
</script>
</body>
</html>
"""

    index_path = HTML_DIR / "index.html"
    index_path.write_text(html, encoding="utf-8")

    # Also drop a tiny data.json for transparency / power users
    (HTML_DIR / "data.json").write_text(json.dumps({
        "global": embed_global,
        "regions": embed_regions,
        "nations": embed_nations
    }, indent=2), encoding="utf-8")

    print(f"\nHTML atlas written to: {index_path}")
    print(f"Vector maps (SVG): {MAPS_DIR} (global.svg + 22 regional *.svg)")
    print("Open outputs/html-atlas/index.html in a browser. All interaction (table, regions, bars) runs in the client.")
    return index_path

def main():
    print("Preparing data (reusing exact same capped 2026 numbers as the print atlas)...")
    data = prepare_atlas_data()
    build_html_atlas(data)
    print("Done.")

if __name__ == "__main__":
    main()
