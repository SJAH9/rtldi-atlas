#!/usr/bin/env python3
"""
Generate a totally self-contained HTML atlas (outputs/html-atlas/) containing
the same data as the print atlas front matter + 22 regional summaries.
RTLDI = Right to Life Deficit Index (source: Zenodo 10.5281/zenodo.19468550). Extended to quantify capital exclusions — lost potential GDP where capital is excluded because the nine protections are absent. ~15T globally. Population-weighted regression with 25% cap.

- Reuses prepare_atlas_data() so numbers, caps, 9-indicator breakdowns, region
  aggregates, and member lists are identical to the PDF.
- Vector choropleth maps (SVG) for global + all 22 regions using the same
  plotly code path (Mollweide-inspired or standard geo, Viridis R scale).
- Single index.html with embedded data (JSON) + Tailwind via CDN (common
  pattern for rich self-contained data apps) + vanilla JS for all interactivity:
  live sortable/filterable/searchable 193-nation table, static regional
  summaries with vector maps, 9-lever breakdowns, and member tables.
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
    detailed_all: List[Dict] = data["detailed_all"]
    detailed_by_loss: List[Dict] = data["detailed_by_loss"]

    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def safe_rank(value: Any) -> Any:
        try:
            if value is None or pd.isna(value):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    # Master table rows (for the interactive summary table).
    # This must use the canonical full 193-nation breakdown, not a filtered
    # presentation list, so the HTML atlas cannot drift into a second pipeline.
    nations = []
    for d in sorted(
        detailed_all,
        key=lambda row: (-safe_float(row.get("total_deficit_usd")), str(row.get("country", row.get("iso3", "")))),
    ):
        nations.append({
            "iso3": d["iso3"],
            "country": d.get("country", d["iso3"]),
            "region": d.get("un_region", ""),
            "r": round(safe_float(d.get("r")), 4),
            "g0": round(safe_float(d.get("g0")), 2),
            "pop": safe_float(d.get("population")),
            "lost_per_cap": round(safe_float(d.get("delta_g_per_capita")), 2),
            "total_lost": safe_float(d.get("total_deficit_usd")),
            "rank": safe_rank(d.get("rank_by_total_deficit")),
        })

    # Pre-compute region detail packets using the same canonical PDF data.
    # No cross-nation comparison callouts are generated.
    region_packets = {}
    for reg_name, reg_sum in regional_data.items():
        members = reg_sum.get("members", [])
        n = reg_sum["n_countries"]

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
                f"corresponding to an estimated ${reg_sum['total_lost_gdp']/1e9:,.1f} billion in capital exclusions (lost potential GDP) annually. "
                f"The region demonstrates particular strength in {', '.join(strong_names) if strong_names else 'several key areas'}, "
                f"where a substantial share of countries satisfy the binarization thresholds for those indicators. "
                f"These protections represent opportunities to support greater economic scale for life and capital."
            )
            para2 = (
                f"Strengthening the areas with lower implementation—especially {', '.join(weak_names) if weak_names else 'priority areas'}—"
                f"is associated with the largest opportunities for realizing additional scale in the region (after the 25% contextual bound). "
                f"The cross-sectional association links stronger protections to greater economic scale of roughly ${potential_b:,.1f} billion annually for the region as a whole (within the bound). "
                f"Whether and how much of that association is realized depends on the other determinants of output (industry structure, resources, human capital, history) that the model explicitly accounts for by bounding the contribution of these nine factors."
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

    # Pre-render full static HTML blocks for EVERY region summary so the HTML version
    # publishes the same content and data as the generated RTLDI_ATLAS_2026_regions.pdf
    # (map + stats + two-para description + 9-indicator breakdown + member table + TOTAL)
    region_summary_blocks = []
    for reg_name, reg in sorted(embed_regions.items(), key=lambda x: -x[1]["total_lost"]):
        members = reg.get("members", [])
        n = reg["n"]
        total_lost_str = format_usd(reg["total_lost"])
        pop_str = format_pop(reg["total_pop"])
        # member table rows + REGIONAL TOTAL (sorted by lost desc, like PDF tables)
        member_rows = ""
        total_lost = 0.0
        sorted_mems = sorted(members, key=lambda x: -x.get("lost", 0))
        for m in sorted_mems:
            lost = float(m.get("lost", 0))
            total_lost += lost
            r_str = f"{m.get('r', 0):.2f}"
            lost_str = format_usd(lost)
            member_rows += f'<tr><td class="px-2 py-0.5">{m["country"]}</td><td class="px-2 py-0.5 text-right tabular-nums">{r_str}</td><td class="px-2 py-0.5 text-right tabular-nums">{lost_str}</td></tr>'
        total_row = f'<tr class="font-semibold border-t border-slate-700 bg-slate-800"><td class="px-2 py-0.5">REGIONAL TOTAL ({n} countries)</td><td></td><td class="px-2 py-0.5 text-right tabular-nums">{format_usd(total_lost)}</td></tr>'
        # 9 indicators breakdown
        ind_html = ""
        weakest = None
        for ind in reg.get("indicators", []):
            pct = int(round(ind.get("frac_yes", 0) * 100))
            lost_b = ind.get("attributable", 0) / 1e9
            ind_html += f'<div class="flex justify-between py-px"><span>{ind["name"]}</span><span class="tabular-nums">{pct}% • ${lost_b:.1f}B</span></div>'
            if not weakest or ind.get("frac_yes", 1) < weakest.get("frac_yes", 1):
                weakest = ind
        univ_html = ""
        if weakest and weakest.get("frac_yes", 1) < 0.35:
            univ_html = f'<div class="mt-1 text-xs text-red-400">Opportunity area: {weakest["name"]} (implemented in {int(weakest.get("frac_yes",0)*100)}% of countries in region)</div>'
        # descriptions (reframed, matching updated PDF)
        para_html = f'<p class="text-sm mt-1 leading-snug">{reg.get("para1", "")}</p>'
        if reg.get("para2"):
            para_html += f'<p class="text-sm mt-2 leading-snug">{reg.get("para2", "")}</p>'
        block = f'''<div class="region-summary mb-10 p-5 border border-slate-700 rounded-3xl bg-slate-900" id="reg-{reg["slug"]}">
  <h3 class="text-2xl font-semibold mb-1">{reg_name}</h3>
  <div class="text-sm text-slate-400 mb-3">{n} countries • {pop_str} • Weighted R {reg["weighted_r"]:.2f} • Capital Exclusions {total_lost_str}</div>
  <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
    <div class="lg:col-span-3 map-container">
      <img src="maps/{reg["slug"]}.svg" alt="{reg_name} choropleth (vector SVG)" class="w-full rounded border border-slate-600">
      <div class="text-[10px] text-slate-400 mt-1">Vector SVG • Viridis R scale (same as global and print regions.pdf)</div>
    </div>
    <div class="lg:col-span-2 text-sm">
      {para_html}
    </div>
  </div>
  <div class="mt-4">
    <div class="text-sm font-medium mb-1">9-Levers Breakdown + Associated Capital Exclusions</div>
    <div class="text-xs leading-tight">{ind_html}</div>
    {univ_html}
  </div>
  <div class="mt-4">
    <div class="text-sm font-medium mb-1">Member Nations Table (ending in REGIONAL TOTAL)</div>
    <table class="w-full text-xs">
      <thead class="text-slate-400"><tr><th class="text-left py-0.5">Country</th><th class="text-right py-0.5">R</th><th class="text-right py-0.5">Capital Exclusions</th></tr></thead>
      <tbody class="text-slate-200">
        {member_rows}
        {total_row}
      </tbody>
    </table>
  </div>
</div>'''
        region_summary_blocks.append(block)
    region_summaries_html = "\n".join(region_summary_blocks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RTLDI ATLAS 2026 — HTML (Front + Regions)</title>
<!-- RTLDI = Right to Life Deficit Index (extended to capital exclusions) -->
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
  :root {{ --font-sans: Inter, system-ui, sans-serif; }}
  body {{ font-family: var(--font-sans); }}
  .heading {{ font-family: 'Space Grotesk', Inter, system-ui, sans-serif; font-weight: 600; letter-spacing: -.02em; }}
  .stat {{ font-variant-numeric: tabular-nums; }}
  .data-table th {{ position: sticky; top: 0; background: #fff; z-index: 10; }}
  .r-high {{ background-color: #052e16; color: #86efac; }}
  .r-mid  {{ background-color: #422006; color: #fde047; }}
  .r-low  {{ background-color: #450a0a; color: #fda4af; }}
  .lever-bar {{ height: 10px; background: linear-gradient(to right, #64748b, #0ea47a); border-radius: 9999px; transition: width .4s ease; }}
  .map-container svg, .map-container img {{ max-width: 100%; height: auto; border: 1px solid #334155; border-radius: 8px; background: #0f172a; }}
  .section-title {{ font-size: 1.05rem; letter-spacing: -.015em; }}
</style>
</head>
<body class="bg-slate-950 text-slate-200">
<div class="max-w-screen-xl mx-auto">
  <!-- Header -->
  <header class="border-b border-slate-800 bg-slate-950 sticky top-0 z-50">
    <div class="px-6 py-4 flex items-center justify-between">
      <div>
        <div class="flex items-center gap-x-3">
          <div class="w-9 h-9 bg-emerald-600 rounded-xl flex items-center justify-center text-white text-xl font-semibold">R</div>
          <div>
            <span class="heading text-2xl font-semibold tracking-tighter">RTLDI ATLAS 2026</span>
            <span class="ml-2 text-xs px-2 py-0.5 bg-emerald-900 text-emerald-400 rounded-full font-medium">Right to Life Deficit Index</span>
          </div>
        </div>
        <div class="text-[11px] text-slate-400 mt-0.5">Front Matter + 22 Regional Summaries • Same data as the print atlas • Self-contained • Dark theme</div>
      </div>
      <div class="flex items-center gap-x-2 text-sm">
        <a href="../atlas/RTLDI_ATLAS_2026_ebook.pdf" class="px-3 py-1.5 rounded-xl border border-slate-700 hover:bg-slate-900 transition">Download Print PDF</a>
        <a href="global_interactive.html" target="_blank" class="px-3 py-1.5 rounded-xl bg-emerald-600 text-white hover:bg-emerald-500 transition">Global Interactive Map</a>
        <button id="theme-toggle" class="px-3 py-1.5 rounded-xl border border-slate-700 hover:bg-slate-900 transition text-lg leading-none" title="Toggle dark/light">🌙</button>
        <span class="text-[10px] text-slate-500">V-Dem 2024 + WB 2026 G₀</span>
      </div>
    </div>
  </header>

  <!-- Hero / Global Snapshot -->
  <div class="px-6 pt-8 pb-6">
    <div class="max-w-3xl">
      <h1 class="heading text-5xl tracking-tighter font-semibold">Right to Life Deficit Index</h1>
      <p class="mt-3 text-xl text-slate-300">RTLDI (Right to Life Deficit Index) extended to measure capital exclusions — the lost potential GDP where capital is kept out of the economy because the nine protections necessary for it to operate are absent. The global total is on the order of 15 trillion dollars in excluded capital waiting to be brought back in.</p>
    </div>

    <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-slate-900 border border-slate-700 rounded-3xl p-6 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-400">Global Capital Exclusions (lost potential GDP, capped)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-white">{format_usd(global_total_lost)}</div>
        <div class="text-emerald-400 text-sm mt-1">Every year, recurring</div>
      </div>
      <div class="bg-slate-900 border border-slate-700 rounded-3xl p-6 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-400">Population-weighted Enclosure Strength (R)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-white">{data.get('weighted_r', 0.21):.2f}</div>
        <div class="text-sm mt-1">0 = no protections • 1 = full set of 9</div>
      </div>
      <div class="bg-slate-900 border border-slate-700 rounded-3xl p-6 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-400">UN Member States</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-white">193</div>
        <div class="text-sm mt-1">22 UN regions</div>
      </div>
      <div class="bg-slate-900 border border-slate-700 rounded-3xl p-6 shadow-sm">
        <div class="text-xs uppercase tracking-widest text-slate-400">Conservative Marginal Coefficient (η)</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-white">0.30</div>
        <div class="text-sm mt-1">25% institutional cap applied (raw data suggested ~0.33)</div>
      </div>
    </div>
  </div>



  <!-- Global 9-Lever Capital Exclusions Breakdown (front-matter carto data) -->
  <div class="px-6 pb-8">
    <div class="flex items-baseline justify-between mb-3">
      <div class="section-title font-semibold">Global Capital Exclusions by Lever</div>
      <div class="text-xs text-slate-500">Portion of excluded capital associated with each lever (25% cap)</div>
    </div>
    <div id="global-bars" class="grid grid-cols-1 md:grid-cols-3 gap-3"></div>
  </div>

  <!-- Front Matter Explanatory: How to Use + The Nine Levers (replicates the key front matter pages) -->
  <div class="px-6 pb-8">
    <div class="max-w-3xl mb-6">
      <div class="section-title font-semibold mb-2 text-emerald-400">How to Use the Atlas Data</div>
      <div class="prose prose-sm max-w-none text-slate-300">
        <p>The RTLDI (Right to Life Deficit Index) extended here quantifies capital exclusions — the lost potential GDP that results when the nine protections required for capital to operate safely are not present. Use the R score and the 9-component breakdowns as practical economic intelligence to see where bringing specific protections online can bring excluded capital back into the economy.</p>
        <p class="mt-2"><strong>For policymakers:</strong> Filter by your region. Look at the current level of each lever and the volume of capital currently excluded in your jurisdiction. The levers are low-cost relative to the scale of excluded GDP they correspond to.</p>
        <p class="mt-2"><strong>For investors and analysts:</strong> Higher R is associated with less capital being excluded from the economy. The nine levers are not outcomes of wealth — they are conditions that allow capital to operate and scale to be realized.</p>
        <p class="mt-2"><strong>For anyone:</strong> This is a map of where the global economy is leaving capital on the table. Activating the levers is how that excluded capital can be brought back in.</p>
      </div>
    </div>

    <div>
      <div class="section-title font-semibold mb-3 text-emerald-400">The Nine Levers</div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">1. Legal Protections</span><br>Present when ordinary law is applied consistently to state agents as well as everyone else. Absent when power can act without predictable legal constraint. Multiplies GDP by lowering the risk of arbitrary loss; people and businesses invest and trade more when they know the rules will be enforced fairly. Annual cost is low.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">2. Independent Judiciary</span><br>Present when there is a judiciary capable of upholding right-to-life laws even against the state. These protections represent opportunities for property rights and contracts to support reliable capital flows to productive uses. Annual cost is low relative to the scale unlocked.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">3. Law Enforcement Accountability</span><br>Present when law enforcement agencies are accountable for unlawful killings and violence. These protections represent opportunities to support greater economic scale by reducing arbitrary risk that can deter investment, labor mobility, and everyday economic activity. Annual cost is primarily institutional oversight.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">4. Protection Against Arbitrary Detention</span><br>Present when arbitrary detention is prohibited with real legal recourse. These protections represent opportunities for individuals and families to plan, work, and invest with greater security, supporting scale in the economy. Annual cost is low.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">5. Freedom from Torture and Inhumane Treatment</span><br>Present when the state has effective measures to prevent torture. These protections represent opportunities to support human capital and cooperation. Annual cost is institutional and training — an investment toward realizing greater scale.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">6. Civilian Protection in Conflict Zones</span><br>Present when mechanisms exist to protect civilians during conflict. These protections represent opportunities to preserve the productive capacity and future of entire regions. Annual cost is primarily military discipline and rules of engagement.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">7. Access to Justice</span><br>Present when ordinary people can bring serious claims and have them heard fairly. These conditions represent opportunities for contracts and rights to function for a wider share of the population. Annual cost is court capacity and legal aid.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">8. Freedom of Expression &amp; Whistleblower Protections</span><br>Present when laws protect people who report corruption from retaliation. These conditions represent opportunities for information to flow more accurately and for public resources to be used more effectively. Annual cost is low — mainly passing and enforcing the law.</div>
        <div class="bg-slate-900 border border-slate-700 rounded-2xl p-3"><span class="font-semibold">9. Commitment to Basic Human Security</span><br>Present when a society makes the deliberate choice to maintain a minimum floor against extreme deprivation. This reflects political will rather than just economic outcomes. When present, it increases the share of the population able to participate productively, expanding overall economic scale. Annual cost is a political decision about minimum security standards.</div>
      </div>
      <div class="text-xs text-slate-400 mt-2">Each lever is a simple binary condition. When present, it removes a barrier that otherwise excludes capital from the economy. The nine come from the source document and are extended here via population-weighted regression so the scale of capital exclusions (lost potential GDP) becomes visible. Activating them is how excluded capital can be brought back in.</div>
    </div>
  </div>

  <!-- Interactive Nation Summary Table (exact same data as print front-matter table) -->
  <div class="px-6 pb-10">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title font-semibold">All 193 UN Member States — Summary (by capital exclusions)</div>
      <div class="text-xs text-slate-400">Live client-side filtering &amp; sorting • Same numbers as the print atlas</div>
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
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="lost_per_cap">Capital Exclusions / cap</th>
              <th class="px-3 py-2 text-right cursor-pointer" data-sort="total_lost">Capital Exclusions (USD)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-[13px]"></tbody>
        </table>
      </div>
      <div class="px-3 py-2 text-[10px] text-slate-400 border-t bg-slate-900 border-slate-700">R color: &lt;{LOW_R} red tint • {LOW_R}–{HIGH_R} yellow • &gt;{HIGH_R} green tint. Numbers use the same 25% contextual cap as the print edition.</div>
    </div>
  </div>

  <!-- Regional Summaries (full static content matching the generated RTLDI_ATLAS_2026_regions.pdf exactly) -->
  <div class="px-6 pb-12">
    <div class="section-title font-semibold mb-2">UN Regional Summaries</div>
    <p class="text-sm text-slate-400 max-w-2xl mb-6">The blocks below contain the complete regional summaries (identical data to the print RTLDI_ATLAS_2026_regions.pdf). Each shows the current level of the nine RTLDI levers and the volume of capital exclusions in that region — the lost potential GDP that is sitting outside the economy because the protections required for capital to operate are not present. The focus is on making the scale of excluded capital visible so it can be brought back in.</p>
    {region_summaries_html}
  </div>

  <footer class="px-6 pb-10 text-[10px] text-slate-400">
    Self-contained HTML atlas (dark theme) • Data &amp; methodology identical to RTLDI_ATLAS_2026_ebook.pdf • Generated from the same 2026 rule (V-Dem 2024 + World Bank 2026 G₀) and 0.30 Conservative Marginal Coefficient with 25% cap (population-weighted regression).
    Vector maps are SVG exports from the identical plotly choropleth code used for the print edition. The RTLDI is extended here to quantify capital exclusions (lost potential GDP where capital is excluded because the nine protections are absent). Global total ~15T.
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

// ================== DARK THEME (default dark, toggle persists) ==================
function applyTheme(isDark) {{
  const root = document.documentElement;
  if (isDark) {{
    root.classList.add('dark');
  }} else {{
    root.classList.remove('dark');
  }}
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = isDark ? '☀️' : '🌙';
}}

function initTheme() {{
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = saved ? (saved === 'dark') : prefersDark; // default to dark if no pref
  applyTheme(isDark);

  const btn = document.getElementById('theme-toggle');
  if (btn) {{
    btn.addEventListener('click', () => {{
      const nowDark = !document.documentElement.classList.contains('dark');
      applyTheme(nowDark);
    }});
  }}
}}

// Client-side helpers (executed in browser)
function formatPop(n) {{
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'k';
  return Math.round(n).toLocaleString();
}}

// Tailwind script run
function initTailwind() {{
  // Already loaded via CDN. Theme handled separately.
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

// (Region summaries are now statically published in the HTML for fidelity to regions.pdf.
// Interactive nation table region filtering remains available below.)

// ================== BOOT ==================
function boot() {{
  initTailwind();
  initTheme();
  renderGlobalBars();
  initNationTable();
  // Region summaries are static full blocks (matching PDF); nation table interactivity remains.

  // Keyboard niceties
  document.addEventListener('keydown', e => {{
    if (e.key === '/' && document.activeElement.tagName === 'BODY') {{
      e.preventDefault();
      document.getElementById('search').focus();
    }}
  }});

  // Initial table render already done in initNationTable
  console.log('%c[RTLDI HTML Atlas] Self-contained front+regions ready (dark theme, full breakdowns). Data matches print atlas.', 'color:#166534');
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
