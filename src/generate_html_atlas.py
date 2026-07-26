#!/usr/bin/env python3
"""
Generate a totally self-contained HTML atlas (outputs/html-atlas/) containing
the same data as the print atlas front matter + 22 regional summaries.
RTLDI = Right to Life Deficit Index (source: Zenodo 10.5281/zenodo.19468550). Extended to quantify capital exclusions — lost potential GDP where capital is excluded because the nine protections are absent. ~15T globally. Population-weighted regression with 25% cap.

- Reuses prepare_atlas_data() so numbers, caps, 9-indicator breakdowns, region
  aggregates, and member lists are identical to the PDF.
- Vector choropleth maps (SVG) for global + all 22 regions using the same
  plotly code path (Mollweide-inspired or standard geo, RTLDI atlas R scale).
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
from html import escape
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
from src.atlas_evidence import (
    VDEM_CODEBOOK_URL,
    VDEM_CORE_URL,
    VDEM_DATASET_URL,
    VDEM_ARCHIVE_URL,
    WORLD_BANK_API_URL,
    WORLD_BANK_DATA_URL,
    evidence_bundle,
)
from src.lever_display import LEVER_DISPLAY, format_compact_usd, lever_description, lever_long_description, lever_name, lever_short
from src.map_geometry import (
    RTLDI_COLOR_SCALE,
    add_map_context_note,
    add_metropolitan_france_trace,
    add_small_country_markers,
    apply_atlas_choropleth_style,
    apply_atlas_geo_style,
    apply_european_france_bounds,
    split_france_for_metropolitan_display,
)
from src.web_ui import (
    SITE_CHROME_CSS,
    THEME_BOOT_SCRIPT,
    THEME_RUNTIME_SCRIPT,
    context_nav,
    site_footer,
    site_header,
)
from src.generate_rdf_atlas import write_rdf_atlas

LOW_R = 0.35
HIGH_R = 0.65

HTML_DIR = Path("outputs/html-atlas")
MAPS_DIR = HTML_DIR / "maps"

def format_usd(n: float) -> str:
    return format_compact_usd(n)

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
    map_df, france = split_france_for_metropolitan_display(df)
    fig = px.choropleth(
        map_df,
        locations="iso3",
        color="r",
        locationmode="ISO-3",
        color_continuous_scale=RTLDI_COLOR_SCALE,
        range_color=(0, 1),
        hover_name="country",
        hover_data={
            "r": ":.2f",
            "total_deficit_usd": ":.0f",
            "delta_g_per_capita": ":.0f",
        },
        title="Enclosure Strength (R) — Global",
    )
    apply_atlas_choropleth_style(fig)
    add_metropolitan_france_trace(fig, france)
    marker_count = add_small_country_markers(fig, map_df, marker_size=5)
    fig.update_layout(
        margin=dict(l=0, r=0, t=34, b=8),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        coloraxis_colorbar=dict(
            title=dict(text="RTLP R<br>(0–1)", font=dict(size=10)),
            len=0.56,
            thickness=10,
            tickvals=[0, 0.25, 0.5, 0.75, 1],
        ),
        title=dict(font=dict(size=15, color="#20384a"), x=0.02, xanchor="left"),
    )
    apply_atlas_geo_style(fig, projection_type="mollweide")
    if marker_count:
        add_map_context_note(fig, f"{marker_count} small states shown with locator points.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(str(out_path), format="svg", width=1200, height=620)
    except Exception as exc:
        if out_path.exists():
            print(f"  Reusing existing global SVG after export failure: {str(exc).splitlines()[0]}")
            return out_path
        raise
    return out_path

def get_regional_svg(region_name: str, members: List[dict], all_df: pd.DataFrame, out_path: Path) -> Path:
    """Regional choropleth SVG focused on the countries in the region (fitbounds)."""
    if not HAS_PLOTLY or not members:
        return out_path
    isos = [m["iso3"] for m in members]
    focus_df = all_df[all_df["iso3"].isin(isos)].copy()
    if focus_df.empty:
        return out_path
    use_native_france = region_name == "Western Europe"
    map_df, france = (focus_df, None) if use_native_france else split_france_for_metropolitan_display(focus_df)

    fig = px.choropleth(
        map_df,
        locations="iso3",
        color="r",
        locationmode="ISO-3",
        color_continuous_scale=RTLDI_COLOR_SCALE,
        range_color=(0, 1),
        hover_name="country",
        hover_data={"r": ":.2f", "total_deficit_usd": ":.0f"},
        title=f"{region_name} — Enclosure Strength (R)",
    )
    apply_atlas_choropleth_style(fig)
    add_metropolitan_france_trace(fig, france)
    marker_count = add_small_country_markers(fig, map_df, marker_size=10, show_text=True)
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=6),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        coloraxis_colorbar=dict(
            title=dict(text="R", font=dict(size=10)),
            len=0.48,
            thickness=10,
            tickvals=[0, 0.5, 1],
        ),
        title=dict(font=dict(size=15, color="#20384a"), x=0.02, xanchor="left"),
    )
    apply_atlas_geo_style(fig, show_grid=True)
    if use_native_france:
        apply_european_france_bounds(fig, kind="western_europe")
    else:
        fig.update_geos(fitbounds="locations")
    if marker_count:
        add_map_context_note(fig, f"Locator layer: {marker_count} small states labeled by ISO3.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(str(out_path), format="svg", width=900, height=520)
    except Exception as exc:
        if out_path.exists():
            print(f"  Reusing existing regional SVG for {region_name} after export failure: {str(exc).splitlines()[0]}")
            return out_path
        raise
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
    evidence = evidence_bundle(data)

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
            strong_names = [lever_name(i["num"], i["name"]) for i in sorted_inds[:2] if i.get("frac_yes", 0) > 0.4]
            weak_names = [lever_name(i["num"], i["name"]) for i in sorted_inds[-2:]]
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
                "name": lever_name(i["num"], i.get("name", "")),
                "short": lever_short(i["num"], i.get("name", "")),
                "desc": lever_description(i["num"], i.get("desc", "")),
                "long_desc": lever_long_description(i["num"], i.get("desc", "")),
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
        "indicator_names": [lever_name(i + 1, name) for i, name in enumerate(indicator_names)],
        "indicator_descs": [lever_description(i + 1, desc) for i, desc in enumerate(indicator_descs)],
    }

    def lever_loss_badge(num: int) -> str:
        lost = global_indicator_losts[num - 1] if 0 < num <= len(global_indicator_losts) else 0
        return (
            '<div class="mt-1 text-xs uppercase tracking-wide text-teal-700">'
            f"Annual global exclusion: <span class=\"font-semibold tabular-nums\">{format_usd(lost)}</span>"
            "</div>"
        )

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
        total_row = f'<tr class="font-semibold border-t border-slate-300 bg-slate-50 text-slate-950"><td class="px-2 py-1">REGIONAL TOTAL ({n} countries)</td><td></td><td class="px-2 py-1 text-right tabular-nums">{format_usd(total_lost)}</td></tr>'
        # 9 indicators breakdown
        ind_html = ""
        weakest = None
        for ind in reg.get("indicators", []):
            pct = int(round(ind.get("frac_yes", 0) * 100))
            ind_html += f'''<div class="lever-row">
  <div class="flex items-start justify-between gap-3 text-[12px]"><span class="font-semibold text-slate-800">{ind["name"]}</span><span class="tabular-nums text-teal-700 font-semibold">{format_usd(ind.get("attributable", 0))}</span></div>
  <div class="mt-1 flex items-center gap-2">
    <div class="h-1.5 bg-slate-100 overflow-hidden flex-1"><div class="h-1.5 bg-teal-600" style="width:{pct}%"></div></div>
    <span class="text-[10px] tabular-nums text-slate-500 w-12 text-right">{pct}% yes</span>
  </div>
  <div class="mt-1 text-[11px] leading-4 text-slate-500">{ind.get("desc", "")}</div>
</div>'''
            if not weakest or ind.get("frac_yes", 1) < weakest.get("frac_yes", 1):
                weakest = ind
        univ_html = ""
        if weakest and weakest.get("frac_yes", 1) < 0.35:
            univ_html = f'<div class="mt-3 border-l-2 border-red-500 bg-red-50 px-3 py-2 text-xs text-red-800">Opportunity area: {weakest["name"]} (implemented in {int(weakest.get("frac_yes",0)*100)}% of countries in region)</div>'
        # descriptions (reframed, matching updated PDF)
        para_html = f'<p class="text-sm mt-1 leading-6 text-slate-700">{reg.get("para1", "")}</p>'
        if reg.get("para2"):
            para_html += f'<p class="text-sm mt-3 leading-6 text-slate-700">{reg.get("para2", "")}</p>'
        block = f'''<section class="region-summary mb-8 border border-slate-200 bg-white" id="reg-{reg["slug"]}">
  <div class="border-b border-slate-200 bg-slate-50 px-5 py-4">
    <h3 class="text-2xl font-semibold tracking-tight text-slate-950">{reg_name}</h3>
    <div class="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
      <div class="bg-white border border-slate-200 px-3 py-2"><span class="block text-slate-500">Countries</span><span class="tabular-nums font-semibold text-slate-950">{n}</span></div>
      <div class="bg-white border border-slate-200 px-3 py-2"><span class="block text-slate-500">Population</span><span class="tabular-nums font-semibold text-slate-950">{pop_str}</span></div>
      <div class="bg-white border border-slate-200 px-3 py-2"><span class="block text-slate-500">Weighted R</span><span class="tabular-nums font-semibold text-teal-700">{reg["weighted_r"]:.2f}</span></div>
      <div class="bg-white border border-slate-200 px-3 py-2"><span class="block text-slate-500">Capital Exclusions</span><span class="tabular-nums font-semibold text-slate-950">{total_lost_str}</span></div>
    </div>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-5 gap-5 p-5">
    <div class="lg:col-span-3 map-container">
      <img src="maps/{reg["slug"]}.svg" alt="{reg_name} choropleth (vector SVG)" class="w-full border border-slate-200 bg-white">
      <div class="text-[10px] text-slate-500 mt-1">Vector SVG • RTLDI atlas R scale, matching the print atlas.</div>
    </div>
    <div class="lg:col-span-2 text-sm">
      {para_html}
    </div>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 px-5 pb-5">
    <div>
      <div class="text-sm font-semibold mb-2 text-slate-950">9-Lever Breakdown</div>
      <div>{ind_html}</div>
    {univ_html}
    </div>
    <div>
      <div class="text-sm font-semibold mb-2 text-slate-950">Member Nations</div>
      <div class="max-h-72 overflow-auto border border-slate-200">
      <table class="w-full text-xs">
      <thead class="sticky top-0 bg-slate-50 text-slate-500"><tr><th class="text-left px-2 py-1">Country</th><th class="text-right px-2 py-1">R</th><th class="text-right px-2 py-1">Capital Exclusions</th></tr></thead>
      <tbody class="divide-y divide-slate-100 text-slate-700">
        {member_rows}
        {total_row}
      </tbody>
    </table>
      </div>
    </div>
  </div>
</section>'''
        region_summary_blocks.append(block)
    region_summaries_html = "\n".join(region_summary_blocks)

    def full_data_rows_html() -> str:
        rows = []
        for d in sorted(detailed_all, key=lambda row: str(row.get("country", row.get("iso3", "")))):
            gdp_per_capita = safe_float(d.get("g0"))
            capital_exclusion_per_capita = safe_float(d.get("delta_g_per_capita"))
            population = safe_float(d.get("population"))
            per_capita_potential = gdp_per_capita + capital_exclusion_per_capita
            annual_gdp = gdp_per_capita * population
            capital_exclusion = safe_float(d.get("total_deficit_usd"))
            annual_potential_gdp = annual_gdp + capital_exclusion
            components = d.get("components", [])
            iso3 = escape(str(d.get("iso3", "")))
            country_name = escape(str(d.get("country", d.get("iso3", ""))))
            lever_cells = []
            for i in range(8, -1, -1):
                value = ""
                if len(components) > i:
                    value = str(int(components[i].get("bin", 0) or 0))
                lever_cells.append(f'<td class="num lever">{value}</td>')
            rows.append(
                "<tr>"
                f'<td class="country"><a href="global_interactive.html?country={iso3}" class="country-link">{country_name}</a></td>'
                f'<td class="num score">{safe_float(d.get("r")):.3f}</td>'
                f'<td class="num">${capital_exclusion:,.0f}</td>'
                f'<td class="num">${annual_potential_gdp:,.0f}</td>'
                f'<td class="num">${annual_gdp:,.0f}</td>'
                f'<td class="num">${per_capita_potential:,.0f}</td>'
                f'<td class="num">${gdp_per_capita:,.0f}</td>'
                f'{"".join(lever_cells)}'
                f'<td>{escape(str(d.get("un_region", "")))}</td>'
                "</tr>"
            )
        return "\n".join(rows)

    def build_full_data_html() -> str:
        lever_headers = "".join(
            f'<th title="{escape(meta["name"])}"><a href="levers.html#lever-{num}">L{num}</a></th>'
            for num, meta in reversed(LEVER_DISPLAY.items())
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The RTLDI Atlas of UN Member States - Data and computed RTLP scores</title>
<link rel="alternate" type="application/rdf+xml" title="RTLDI Atlas 2026 RDF/XML" href="rtldi_atlas_2026.rdf">
{THEME_BOOT_SCRIPT}
<style>
  :root {{
    --ink: #18202b;
    --muted: #5b6770;
    --rule: #c6d1da;
    --panel: #f7fafc;
    --accent: #107e65;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #eef2f5;
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 16.5px;
    line-height: 1.55;
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
    z-index: 20;
    background: rgba(255,255,255,.96);
    border-bottom: 1px solid #d8e0e7;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }}
  .brand-row {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .brand-mark {{
    width: 36px;
    height: 36px;
    background: var(--accent);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 21px;
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
    font-size: 14px;
  }}
  .actions {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
  }}
  .button {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    padding: 7px 10px;
    border: 1px solid #cbd5df;
    background: #fff;
    color: var(--ink);
    text-decoration: none;
    font-size: 14px;
  }}
  .button.primary {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }}
  .button:hover {{ background: #f7fafc; }}
  .button.primary:hover {{ background: #0f6f5b; }}
  main {{ padding: 28px 24px 40px; }}
  .title-block {{
    border-left: 4px solid var(--accent);
    padding-left: 18px;
    max-width: 980px;
    margin-bottom: 24px;
  }}
  .title-block h2 {{
    margin: 0;
    font-size: clamp(2rem, 4vw, 3.3rem);
    line-height: 1;
    letter-spacing: 0;
  }}
  .title-block p {{
    margin: 10px 0 0;
    color: var(--muted);
    font-size: 18px;
  }}
  .table-wrap {{
    border: 1px solid var(--rule);
    overflow: auto;
    max-height: calc(100vh - 250px);
    background: #fff;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.8);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1720px;
  }}
  th, td {{
    border-bottom: 1px solid #e3e8ee;
    padding: 8px 10px;
    text-align: left;
    white-space: nowrap;
  }}
  th {{
    position: sticky;
    top: 0;
    z-index: 1;
    background: #eef6f4;
    color: #475569;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
  }}
  th a {{ color: inherit; text-decoration: none; }}
  th a:hover {{ color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }}
  td {{ font-size: 14px; }}
  th:first-child, td:first-child {{
    position: sticky;
    left: 0;
    z-index: 2;
    box-shadow: 1px 0 0 #e3e8ee;
  }}
  th:first-child {{ z-index: 3; background: #e6f2ef; }}
  td:first-child {{ background: #fff; }}
  tr:nth-child(even) td:first-child {{ background: #fbfdff; }}
  .country {{ font-weight: 650; color: #0f172a; }}
  .country-link {{ color: #0f766e; text-decoration: none; }}
  .country-link:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .score {{ font-weight: 650; color: #0f766e; }}
  .lever {{ text-align: center; }}
  tr:nth-child(even) td {{ background: #fbfdff; }}
  tbody tr:hover td {{ background: #f0fdfa; }}
  tbody tr:hover td:first-child {{ background: #eefbf7; }}
  .note {{
    margin-top: 10px;
    color: var(--muted);
    font-size: 13px;
  }}
  .citation-panel {{
    margin-top: 30px;
    padding-top: 26px;
    border-top: 1px solid var(--rule);
    max-width: 1060px;
  }}
  .citation-panel h3 {{
    margin: 0 0 8px;
    font-size: 22px;
  }}
  .citation-panel p {{ max-width: 920px; }}
  .citation-grid {{
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }}
  .citation-item {{
    padding: 16px;
    border: 1px solid var(--rule);
    background: var(--panel);
  }}
  .citation-item h4 {{ margin: 0 0 7px; font-size: 15px; }}
  .citation-item p {{ margin: 0; color: var(--muted); font-size: 14px; }}
  .citation-text {{
    display: block;
    margin-top: 16px;
    padding: 14px 16px;
    border-left: 4px solid var(--accent);
    background: var(--panel);
    color: var(--ink);
    font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    white-space: normal;
  }}
  @media (max-width: 760px) {{
    main {{ padding: 22px 16px 32px; }}
    .citation-grid {{ grid-template-columns: 1fr; }}
  }}
  html[data-theme="night"] .table-wrap,
  html[data-theme="night"] table,
  html[data-theme="night"] td,
  html[data-theme="night"] td:first-child {{
    background: var(--site-surface) !important;
    color: var(--site-ink);
    border-color: var(--site-rule);
  }}
  html[data-theme="night"] th,
  html[data-theme="night"] th:first-child {{
    background: #172338 !important;
    color: #cbd5e1;
    border-color: var(--site-rule);
  }}
  html[data-theme="night"] tr:nth-child(even) td,
  html[data-theme="night"] tr:nth-child(even) td:first-child {{
    background: #0f172a !important;
  }}
  html[data-theme="night"] tbody tr:hover td,
  html[data-theme="night"] tbody tr:hover td:first-child {{
    background: #13332f !important;
  }}
  html[data-theme="night"] .country,
  html[data-theme="night"] .title-block h2 {{ color: var(--site-ink); }}
  html[data-theme="night"] .citation-item,
  html[data-theme="night"] .citation-text {{
    background: var(--site-surface-soft);
    border-color: var(--site-rule);
    color: var(--site-ink);
  }}
{SITE_CHROME_CSS}
</style>
</head>
<body>
<div class="shell site-shell">
  {site_header("data", "Full Data View")}
  {context_nav("data")}
  <main>
    <section class="title-block">
      <h2>The RTLDI Atlas of UN Member States - Data and computed RTLP scores</h2>
      <p>Single RTLP score, nine binary lever scores, GDP baseline, potential GDP, and annual capital exclusions in USD.</p>
    </section>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nation</th>
            <th>RTLP</th>
            <th>Capital exclusion USD</th>
            <th>Annual potential GDP</th>
            <th>Annual GDP</th>
            <th>Per capita potential</th>
            <th>GDP per capita</th>
            {lever_headers}
            <th>UN Region</th>
          </tr>
        </thead>
        <tbody>
          {full_data_rows_html()}
        </tbody>
      </table>
    </div>
    <div class="note">Lever columns are binary computed RTLP components: 1 means the protection is present under the atlas threshold; 0 means it is absent. Annual GDP and annual potential GDP are computed from GDP per capita, population, and capped capital exclusions used by the print atlas.</div>
    <section class="citation-panel" aria-labelledby="data-citation-heading">
      <h3 id="data-citation-heading">Citing and attributing this table</h3>
      <p>This table combines original RTLDI Project classifications and computed outputs with observations from two public statistical sources. Cite the project and the underlying source appropriate to the fields you use.</p>
      <div class="citation-grid">
        <article class="citation-item"><h4>RTLDI Project fields</h4><p>The RTLP score, RTLDI and capital-exclusion estimates, annual and per-capita potential GDP, and all nine binary lever classifications are attributable to the RTLDI Atlas Project.</p></article>
        <article class="citation-item"><h4>V-Dem source fields</h4><p>The institutional observations used to classify the levers are attributable to the V-Dem Institute. Cite the Country-Year Full+Others v15 dataset and consult the <a href="vdem.html">atlas V-Dem guide</a>.</p></article>
        <article class="citation-item"><h4>World Bank source fields</h4><p>GDP per capita, population, undernourishment, and poverty observations are attributable to the World Bank's World Development Indicators. Consult the <a href="world_bank.html">atlas World Bank guide</a>.</p></article>
      </div>
      <code class="citation-text">RTLDI Atlas Project. (2026). RTLDI Atlas of UN Member States (Version 2026.8.4) [Data set and software]. https://github.com/SJAH9/rtldi-atlas</code>
      <p class="note">The complete project and theoretical-framework citations are provided on the <a href="about.html">About page</a>.</p>
    </section>
  </main>
  {site_footer()}
</div>
{THEME_RUNTIME_SCRIPT}
</body>
</html>
"""

    def reference_page(title: str, eyebrow: str, body: str, active: str) -> str:
        page_label = {
            "levers": "Nine Levers",
            "regression": "Regression & Eta",
            "vdem": "V-Dem Source",
            "world_bank": "World Bank Source",
            "about": "About the Project",
        }.get(active, title)
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | RTLDI Atlas 2026</title>
{THEME_BOOT_SCRIPT}
<style>
:root{{--ink:#18202b;--muted:#5b6770;--rule:#c6d1da;--panel:#f4f8fa;--accent:#107e65;--warn:#9a5a16}}
*{{box-sizing:border-box}}body{{margin:0;background:#eef2f5;color:var(--ink);font:17px/1.6 Inter,system-ui,sans-serif}}
.shell{{max-width:1180px;margin:auto;background:white;min-height:100vh}}
.brand{{display:flex;gap:12px;align-items:center;font-weight:700}}.mark{{width:38px;height:38px;background:var(--accent);color:white;display:grid;place-items:center;font-size:22px}}
nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a,.button{{border:1px solid var(--rule);padding:7px 11px;color:var(--ink);text-decoration:none;font-size:14px}}nav a:hover,.button:hover{{background:var(--panel)}}
main{{padding:42px 24px 70px}}.hero{{border-left:5px solid var(--accent);padding-left:20px;max-width:930px;margin-bottom:34px}}.eyebrow{{color:var(--accent);font-size:13px;font-weight:700;text-transform:uppercase}}h1{{font-size:clamp(2.2rem,5vw,4rem);line-height:1.04;margin:5px 0 12px}}h2{{font-size:1.55rem;margin:36px 0 12px}}h3{{font-size:1.12rem;margin:0 0 8px}}p{{max-width:850px}}.lede{{font-size:20px;color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}}.card{{scroll-margin-top:130px;border:1px solid var(--rule);border-left:4px solid var(--accent);padding:18px;background:white}}.total{{font-size:27px;font-weight:750;font-variant-numeric:tabular-nums}}.meta{{color:var(--muted);font-size:14px}}code{{background:#edf3f5;padding:2px 5px}}.citation-text{{display:block;max-width:900px;padding:14px 16px;border-left:4px solid var(--accent);white-space:normal;font-size:14px;line-height:1.55}}table{{width:100%;border-collapse:collapse;margin:12px 0 24px}}th,td{{border-bottom:1px solid var(--rule);padding:10px;text-align:left;vertical-align:top}}th{{background:var(--panel);font-size:13px;text-transform:uppercase}}.num{{text-align:right;font-variant-numeric:tabular-nums}}.callout{{border:1px solid #e0c18e;border-left:5px solid var(--warn);background:#fff9ef;padding:16px;margin:20px 0}}.bar{{height:10px;background:#dfe8e8;margin-top:10px}}.bar span{{display:block;height:100%;background:var(--accent)}}a{{color:#0f766e}}ul{{padding-left:22px}}.jump-nav{{display:flex;gap:6px;flex-wrap:wrap;margin:22px 0 28px}}.jump-nav a{{min-width:36px;padding:6px 9px;border:1px solid var(--rule);text-align:center;text-decoration:none;font-size:13px;font-weight:700}}@media(max-width:650px){{main{{padding:28px 16px 50px}}}}
html[data-theme="night"] body{{--ink:var(--site-ink);--muted:var(--site-muted);--rule:var(--site-rule);--panel:var(--site-surface-soft);--accent:var(--site-accent);--warn:#f2b766}}
html[data-theme="night"] .card,html[data-theme="night"] td{{background:var(--site-surface);border-color:var(--site-rule)}}html[data-theme="night"] th{{background:var(--site-surface-soft)}}html[data-theme="night"] .callout{{background:#2a2114;border-color:#76552a}}html[data-theme="night"] .bar{{background:#334155}}html[data-theme="night"] h1,html[data-theme="night"] h2,html[data-theme="night"] h3{{color:var(--site-ink)}}
{SITE_CHROME_CSS}
</style></head><body><div class="shell site-shell">{site_header(active, page_label)}{context_nav(active)}<main><section class="hero"><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1></section>{body}</main>{site_footer()}</div>{THEME_RUNTIME_SCRIPT}</body></html>"""

    max_total = max(evidence["lever_totals"].values()) or 1
    lever_cards = []
    for num, meta in LEVER_DISPLAY.items():
        cross = evidence["crosswalk"][num]
        total = evidence["lever_totals"].get(num, 0)
        fields = ", ".join(f"<code>{escape(field)}</code>" for field in cross["fields"])
        lever_cards.append(f"""<article class="card" id="lever-{num}"><div class="eyebrow">Lever {num}</div><h2>{escape(meta['name'])}</h2><div class="total">{format_compact_usd(total)} annually</div><div class="bar"><span style="width:{100*total/max_total:.1f}%"></span></div><p>{escape(meta['long_description'])}</p><h3>RTLP question</h3><p>{escape(cross['question'])}</p><h3>Executable crosswalk</h3><p><strong>{escape(cross['source'])}</strong> · {fields}<br>{escape(cross['transform'])}</p><p class="meta"><strong>Atlas field mapping:</strong> {escape(cross['proxy'])}</p></article>""")
    levers_html = reference_page(
        "The Nine Levers: Fields, Thresholds, and Capital Exclusions",
        "Executable crosswalk",
        f"<p class='lede'>The RTLP equations come from the source material. Nested Causal Modelling identified the nine protections that most track with GDP gains, and this atlas operationalizes and extends that calculation across UN member states using the executable fields below.</p><nav class='jump-nav' aria-label='Jump to lever'>{''.join(f'<a href=\"#lever-{num}\">L{num}</a>' for num in range(1, 10))}</nav><div class='callout'><strong>How to read this page</strong><br>The dollar amount is each lever's globally attributed share after the national 25% cap is allocated. The listed source fields show how the atlas implements each RTLP protection in the released country dataset; they do not replace the source RTLP theory or the NCM identification of the nine protections.</div><div class='grid'>{''.join(lever_cards)}</div>",
        "levers",
    )

    reg = evidence["regression"]
    main_reg = reg["main"]
    growth = reg["growth"]
    comparator_rows = "".join(
        f"<tr><td>{escape(item['label'])}</td><td class='num'>{item['n']}</td><td class='num'>{item['slope']:.3f}</td><td class='num'>{item['r2']:.3f}</td><td class='num'>{item['p']:.3g}</td></tr>"
        for item in reg["comparators"]
    )
    growth_text = "Not available" if not growth else f"n={growth['n']}; slope={growth['slope']:.3f} percentage points per lever; R²={growth['r2']:.3f}; p={growth['p']:.3g}."
    regression_html = reference_page(
        "GDP Regression, Significance, and Eta",
        "Reproducible model evidence",
        f"""<p class="lede">The canonical model is a population-weighted cross-sectional regression of log GDP per capita on the number of activated levers. It estimates association with GDP level, not a causal time-series growth effect.</p>
        <div class="grid"><div class="card"><h3>η (eta)</h3><div class="total">{main_reg['eta']:.3f}</div><p>Implied proportional GDP-per-capita difference per additional activated lever: <code>exp(slope)-1</code>.</p></div><div class="card"><h3>Uncertainty</h3><div class="total">{main_reg['ci_low']:.1%} to {main_reg['ci_high']:.1%}</div><p>Approximate 95% robust interval for η.</p></div><div class="card"><h3>Model fit</h3><div class="total">R² {main_reg['r2']:.3f}</div><p>n={main_reg['n']}; log slope={main_reg['slope']:.3f}; robust SE={main_reg['se']:.3f}; p={main_reg['p']:.3g}.</p></div></div>
        <h2>Exact specification</h2><p><code>log(GDP per capita) = intercept + beta × activated-lever count + error</code>, fitted by population-weighted least squares. <code>η = exp(beta)-1</code>. The atlas rounds the estimated {main_reg['eta']:.3f} to 0.30, then applies <code>ΔG = min(η × (1-R) × G₀, 0.25 × G₀)</code>.</p>
        <div class="callout"><strong>Significance is not causality.</strong> The coefficient is statistically distinguishable from zero in this specification, but cross-sectional omitted variables, reverse causation, proxy reuse, threshold choices, and source-year mismatch remain. The 25% cap limits attribution; it does not solve identification.</div>
        <h2>Comparator checks</h2><table><thead><tr><th>Single predictor</th><th class="num">n</th><th class="num">Slope</th><th class="num">R²</th><th class="num">p</th></tr></thead><tbody>{comparator_rows}</tbody></table><p class="meta">These unweighted, one-predictor comparisons use log GDP per capita as the outcome. Undernourishment and poverty are themselves development outcomes and lever 9 inputs, so they are descriptive comparators, not independent controls. Different sample sizes reflect missing data.</p>
        <h2>Growth falsification check</h2><p>{growth_text}</p><p>The available 2023–2024 current-US$ change does <strong>not</strong> show a statistically significant relationship with lever count. This is why the atlas describes a strong association with the cross-sectional GDP level and does not claim that the nine levers predict one-year GDP growth.</p>""",
        "regression",
    )

    vdem_html = reference_page(
        "V-Dem Data Used by the Atlas",
        "Dataset provenance",
        f"""<p class="lede">The committed 2026 score table identifies V-Dem Country-Year Full+Others v15 as its source and uses 2024 country-year observations. The large raw CSV is not redistributed in this repository.</p><div class="grid"><div class="card"><h3>Published score provenance</h3><div class="total">V-Dem v15</div><p>Full+Others country-year file; observation year 2024.</p></div><div class="card"><h3>Current update workflow</h3><div class="total">V-Dem v16</div><p>Core is sufficient for current fields; Full+Others is also accepted.</p></div></div><h2>Download and rebuild</h2><ol><li>For the committed release vintage, open the <a href="{VDEM_ARCHIVE_URL}">official V-Dem archive</a> and obtain Country-Year Full+Others v15 in CSV format.</li><li>For a current-data update, open the <a href="{VDEM_DATASET_URL}">official dataset page</a> and choose <a href="{VDEM_CORE_URL}">Country-Year Core v16</a>.</li><li>Extract the CSV into <code>data/raw/</code> using the matching v15 or v16 filename.</li><li>Run <code>python3 -m src.build_atlas --year 2026 --eta 0.30</code>.</li></ol><p>Use the codebook distributed with the chosen dataset; the <a href="{VDEM_CODEBOOK_URL}">official v16 codebook</a> documents the current release. V-Dem model-estimate columns are latent interval estimates, not original 0–4 coder categories.</p><div class="callout"><strong>Replication boundary:</strong> a v16 rebuild is a refreshed analysis and may revise scores because V-Dem re-estimates historical values between releases. Bit-for-bit replication requires the exact archived v15 source file and its checksum; that checksum is not present in the repository.</div>""",
        "vdem",
    )

    world_bank_html = reference_page(
        "World Bank Data Used by the Atlas",
        "Dataset provenance",
        f"""<p class="lede">World Development Indicators supply the GDP baseline, population, undernourishment, and poverty values used by the 2026 atlas.</p><table><thead><tr><th>Field</th><th>Indicator</th><th>Role</th></tr></thead><tbody><tr><td>GDP per capita</td><td><code>NY.GDP.PCAP.CD</code></td><td>G₀ baseline and regression outcome</td></tr><tr><td>Population</td><td><code>SP.POP.TOTL</code></td><td>Regression weight and national aggregation</td></tr><tr><td>Undernourishment</td><td><code>SN.ITK.DEFC.ZS</code></td><td>Lever 9 input</td></tr><tr><td>Extreme poverty</td><td><code>SI.POV.DDAY</code></td><td>Lever 9 input</td></tr></tbody></table><h2>Download and rebuild</h2><p>Each indicator can be downloaded as CSV, XML, or Excel from the <a href="{WORLD_BANK_DATA_URL}">World Bank Data portal</a>. The build pipeline uses the public <a href="{WORLD_BANK_API_URL}">World Bank API</a> through <code>wbgapi</code> and stores processed snapshots under <code>data/processed/</code>. Run <code>python3 -m src.fetch_wb</code> for a small connectivity check, then the canonical atlas build command.</p><div class="callout"><strong>Vintage and missingness:</strong> “2026 baseline” means the freshest published value available when the atlas was built, not that every observation was measured in 2026. Missing undernourishment or poverty is conservatively scored as lever 9 absent. Current-US$ GDP is appropriate for the atlas's current-dollar totals but includes exchange-rate and price-level movement.</div>""",
        "world_bank",
    )

    about_html = reference_page(
        "About the RTLDI Atlas",
        "Project, authorship, and citation",
        """<p class="lede">The RTLDI Atlas is an open, reproducible atlas of the conditions that protect human life and allow capital to operate across all 193 United Nations Member States.</p>
        <h2>Origins and purpose</h2>
        <p>The project originates in Sid J.A. Hubbard's <a href="https://doi.org/10.5281/zenodo.19468550"><em>Causality and Attraction: A Continuum of Steady States</em>, Volume I</a>. The Atlas operationalizes the book's Right-to-Life Protection method: it translates nine institutional protections into country-level classifications, an RTLP score, the Right to Life Deficit Index, and estimates of capital excluded when those protections are absent.</p>
        <p>The Atlas is a practice in Nested Causal Modelling and is specifically a <strong>Level 4 NCM Intervention</strong>. It moves from a causal framework to a public operational system: an inspectable crosswalk, reproducible scoring pipeline, national and global data products, maps, and intervention surfaces that make the modeled constraints visible.</p>
        <div class="grid">
          <article class="card"><div class="eyebrow">Framework</div><h3>Causality and Attraction, Volume I</h3><p>The source of the RTLP equations, nine protections, and nested causal interpretation.</p><a class="button" href="https://doi.org/10.5281/zenodo.19468550">Open on Zenodo</a></article>
          <article class="card"><div class="eyebrow">Book</div><h3>Nested Causal Modelling</h3><p><em>Nested Causal Modelling: Solving Impossible Problems</em> presents the broader intervention method and its three-part framework.</p><a class="button" href="https://www.amazon.com/dp/B0H8K4C3S6">Amazon</a> <a class="button" href="https://elevenreader.io/audiobooks/nested-causal-modelling-audiobook/8Mj5lsaUYs3WwjKAn1Xu">ElevenReader audiobook</a></article>
          <article class="card"><div class="eyebrow">Open project</div><h3>Code, data, and releases</h3><p>The source, processing pipeline, documentation, generated data, and release history are publicly inspectable.</p><a class="button" href="https://github.com/SJAH9/rtldi-atlas">View the GitHub repository</a></article>
        </div>
        <h2>Principal Investigator</h2>
        <p><strong>Sid J.A. Hubbard</strong> is the Principal Investigator of the RTLDI Atlas Project. He is an independent research technologist designing mathematical and architectural interventions for systemic complexity across economics, governance, technology, and AI.</p>
        <p><a href="https://sidhubbard.com/">Investigator website</a> · <a href="https://sidhubbard.com/#interventions">Intervention case studies</a> · <a href="https://www.linkedin.com/in/sidhubbard">LinkedIn profile</a></p>
        <div class="callout"><strong>Production disclosure.</strong> At this stage, the entirety of the Atlas project is written, directed, and engineered by its Principal Investigator with the assistance of multiple AI and data-science tools used in research, software development, analysis, validation, and production. Responsibility for the project's methods, decisions, interpretations, and releases rests with the Principal Investigator.</div>
        <h2>Open source and rights</h2>
        <p>The RTLDI Atlas repository, including its code, data-processing pipeline, documentation, and generated outputs, is open source under the <a href="https://github.com/SJAH9/rtldi-atlas/blob/main/LICENSE">MIT License</a>. The license permits use, modification, redistribution, and commercial use while requiring preservation of the copyright and license notice.</p>
        <p>The underlying theoretical framework and book content are separate works. <em>Causality and Attraction</em> remains under its original copyright and CC BY-NC-ND 4.0 terms; it is not relicensed by the Atlas repository's MIT License.</p>
        <h2>How to cite the Atlas</h2>
        <code class="citation-text">RTLDI Atlas Project. (2026). RTLDI Atlas of UN Member States (Version 2026.8.4) [Data set and software]. Sid J.A. Hubbard, Principal Investigator. https://github.com/SJAH9/rtldi-atlas</code>
        <p>For the source theory, also cite Hubbard, Sid J.A. (2026), <em>Causality and Attraction: A Continuum of Steady States</em>, Volume I, Version 3, <a href="https://doi.org/10.5281/zenodo.19468550">doi:10.5281/zenodo.19468550</a>. Field-level attribution for the combined table is documented in the <a href="full_data.html#data-citation-heading">Full Data View</a>.</p>""",
        "about",
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RTLDI ATLAS 2026 — HTML (Front + Regions)</title>
<link rel="alternate" type="application/rdf+xml" title="RTLDI Atlas 2026 RDF/XML" href="rtldi_atlas_2026.rdf">
{THEME_BOOT_SCRIPT}
<!-- RTLDI = Right to Life Deficit Index (extended to capital exclusions) -->
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
  :root {{ --font-sans: Inter, system-ui, sans-serif; }}
  html {{ font-size: 17px; }}
  body {{ font-family: var(--font-sans); font-size: 1rem; line-height: 1.55; }}
  .heading {{ font-family: 'Space Grotesk', Inter, system-ui, sans-serif; font-weight: 600; }}
  .stat {{ font-variant-numeric: tabular-nums; }}
  .data-table th {{ position: sticky; top: 0; background: #f8fafc; z-index: 10; }}
  .r-high {{ background-color: #f0fdf4; }}
  .r-mid  {{ background-color: #fffbeb; }}
  .r-low  {{ background-color: #fff1f2; }}
  .lever-bar {{ height: 10px; background: linear-gradient(to right, #0f766e, #14b8a6); transition: width .4s ease; }}
  .map-container svg, .map-container img {{ max-width: 100%; height: auto; }}
  .section-title {{ font-size: 1.18rem; }}
  .lever-row {{ border: 1px solid #e2e8f0; background: #fff; padding: .85rem; margin-bottom: .65rem; }}
  .lever-card {{ display: flex; flex-direction: column; min-height: 100%; }}
  .lever-card-kicker {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: #0f766e; }}
  .lever-card-body {{ font-size: .98rem; line-height: 1.55; }}
  [class*="text-xs"] {{ font-size: .82rem !important; }}
  [class*="text-sm"] {{ font-size: .96rem !important; }}
  [class*="text-[10px]"] {{ font-size: .74rem !important; }}
  [class*="text-[11px]"] {{ font-size: .78rem !important; }}
  [class*="text-[12px]"] {{ font-size: .86rem !important; }}
  body, body * {{ transition: background-color .35s ease, border-color .35s ease, color .35s ease; }}
  body.night-mode {{ background: #08111f !important; color: #e5edf7 !important; }}
  body.night-mode .max-w-screen-xl,
  body.night-mode .bg-white,
  body.night-mode .bg-slate-50,
  body.night-mode .bg-slate-100,
  body.night-mode .bg-teal-50,
  body.night-mode .lever-row,
  body.night-mode header {{
    background-color: #111827 !important;
  }}
  body.night-mode .border,
  body.night-mode .border-b,
  body.night-mode .border-t,
  body.night-mode .border-l-4,
  body.night-mode .border-slate-100,
  body.night-mode .border-slate-200,
  body.night-mode .border-slate-300,
  body.night-mode .border-teal-100 {{
    border-color: #334155 !important;
  }}
  body.night-mode .text-slate-950,
  body.night-mode .text-slate-900,
  body.night-mode .text-slate-800,
  body.night-mode .text-slate-700 {{
    color: #e5edf7 !important;
  }}
  body.night-mode .text-slate-600,
  body.night-mode .text-slate-500,
  body.night-mode .text-slate-400 {{
    color: #94a3b8 !important;
  }}
  body.night-mode .text-teal-800,
  body.night-mode .text-teal-700 {{
    color: #5eead4 !important;
  }}
  body.night-mode input,
  body.night-mode select,
  body.night-mode button {{
    background-color: #0f172a !important;
    border-color: #334155 !important;
    color: #e5edf7 !important;
  }}
  body.night-mode .r-high {{ background-color: #123524 !important; }}
  body.night-mode .r-mid {{ background-color: #3a2c0a !important; }}
  body.night-mode .r-low {{ background-color: #3b1118 !important; }}
  body.night-mode .divide-y > :not([hidden]) ~ :not([hidden]) {{ border-color: #1f2937 !important; }}
  body.night-mode .shadow-sm {{ box-shadow: 0 0 0 1px rgba(51,65,85,.7) !important; }}
  body.night-mode .map-container img {{ background: #0f172a !important; border-color: #334155 !important; }}
{SITE_CHROME_CSS}
</style>
</head>
<body class="bg-slate-100 text-slate-900">
<div class="max-w-screen-xl mx-auto bg-white min-h-screen shadow-sm site-shell">
  {site_header("overview", "Global Overview")}

  <!-- Hero / Global Snapshot -->
  <div class="px-6 pt-8 pb-6">
    <div class="max-w-4xl border-l-4 border-teal-700 pl-5">
      <h1 class="heading text-5xl font-semibold text-slate-950">Right to Life Deficit Index</h1>
      <p class="mt-3 text-xl text-slate-600 leading-8">RTLDI extended to measure capital exclusions: the lost potential GDP where capital is kept out of the economy because the nine protections necessary for it to operate are absent.</p>
    </div>

    <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="bg-slate-50 border border-slate-200 p-5">
        <div class="text-xs uppercase tracking-wider text-slate-500">Global Capital Exclusions</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-slate-950">{format_usd(global_total_lost)}</div>
        <div class="text-teal-700 text-sm mt-1">annual, capped</div>
      </div>
      <div class="bg-slate-50 border border-slate-200 p-5">
        <div class="text-xs uppercase tracking-wider text-slate-500">Population-weighted R</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-slate-950">{data.get('weighted_r', 0.21):.2f}</div>
        <div class="text-sm mt-1 text-slate-500">0 none • 1 full set</div>
      </div>
      <div class="bg-slate-50 border border-slate-200 p-5">
        <div class="text-xs uppercase tracking-wider text-slate-500">UN Member States</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-slate-950">193</div>
        <div class="text-sm mt-1 text-slate-500">22 UN regions</div>
      </div>
      <div class="bg-slate-50 border border-slate-200 p-5">
        <div class="text-xs uppercase tracking-wider text-slate-500">Coefficient eta</div>
        <div class="mt-1 text-4xl font-semibold tabular-nums stat text-slate-950">0.30</div>
        <div class="text-sm mt-1 text-slate-500">25% institutional cap</div>
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
      <div class="section-title font-semibold mb-2 text-teal-800">How to Use the Atlas Data</div>
      <div class="text-sm max-w-none text-slate-700 leading-6">
        <p>The RTLDI (Right to Life Deficit Index) extended here quantifies capital exclusions — the lost potential GDP that results when the nine protections required for capital to operate safely are not present. Use the R score and the 9-component breakdowns as practical economic intelligence to see where bringing specific protections online can bring excluded capital back into the economy.</p>
        <p class="mt-2"><strong>For policymakers:</strong> Filter by your region. Look at the current level of each lever and the volume of capital currently excluded in your jurisdiction. The levers are low-cost relative to the scale of excluded GDP they correspond to.</p>
        <p class="mt-2"><strong>For investors and analysts:</strong> Higher R is associated with less capital being excluded from the economy. The nine levers are not outcomes of wealth — they are conditions that allow capital to operate and scale to be realized.</p>
        <p class="mt-2"><strong>For anyone:</strong> This is a map of where the global economy is leaving capital on the table. Activating the levers is how that excluded capital can be brought back in.</p>
      </div>
    </div>

    <div>
      <div class="section-title font-semibold mb-3 text-teal-800">The Nine Levers</div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
        {''.join(f'<a href="levers.html#lever-{num}" class="lever-card bg-white border border-slate-200 p-4 no-underline hover:border-teal-600"><div class="lever-card-kicker">Lever {num}</div><span class="font-semibold text-slate-950">{meta["name"]}</span>{lever_loss_badge(num)}<div class="lever-card-body mt-2 text-slate-600">{meta["long_description"]}</div></a>' for num, meta in LEVER_DISPLAY.items())}
      </div>
      <div class="text-xs text-slate-400 mt-3">Each lever is a simple binary condition. When present, it removes a barrier that otherwise excludes capital from the economy. The nine come from the source document and are extended here via population-weighted regression so the scale of capital exclusions (lost potential GDP) becomes visible. Activating them is how excluded capital can be brought back in.</div>
    </div>
  </div>

  <!-- Data exploration links -->
  <div class="px-6 pb-10">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title font-semibold">Explore the National Data</div>
      <div class="text-xs text-slate-400">Static data view + interactive map</div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="bg-white border border-slate-200 border-l-4 border-l-teal-700 p-5 flex flex-col gap-4">
        <div>
          <div class="font-semibold text-slate-950">Interactive Map</div>
          <div class="text-sm text-slate-500 mt-1">Click a country to load national data, capital exclusions, and the nine-lever breakdown below the map.</div>
        </div>
        <a href="global_interactive.html" target="_blank" class="inline-flex items-center justify-center px-4 py-2 bg-teal-700 text-white hover:bg-teal-800 transition mt-auto">Open Interactive Map</a>
      </div>
      <div class="bg-white border border-slate-200 border-l-4 border-l-teal-700 p-5 flex flex-col gap-4">
        <div>
          <div class="font-semibold text-slate-950">Full Data View</div>
          <div class="text-sm text-slate-500 mt-1">Open the complete alphabetized table for all UN member states, computed RTLP scores, nine levers, GDP, potential GDP, and capital exclusions.</div>
        </div>
        <a href="full_data.html" class="inline-flex items-center justify-center px-4 py-2 border border-slate-300 text-slate-900 hover:bg-slate-50 transition mt-auto">Open Full Data View</a>
      </div>
      <div class="bg-white border border-slate-200 border-l-4 border-l-teal-700 p-5 flex flex-col gap-4">
        <div><div class="font-semibold text-slate-950">Methods and Source Data</div><div class="text-sm text-slate-500 mt-1">Inspect every lever field and threshold, the GDP regression and eta, and exact V-Dem and World Bank download paths.</div></div>
        <a href="levers.html" class="inline-flex items-center justify-center px-4 py-2 border border-slate-300 text-slate-900 hover:bg-slate-50 transition mt-auto">Open Methods & Sources</a>
      </div>
    </div>
  </div>

  <!-- Regional Summaries (full static content matching the generated RTLDI_ATLAS_2026_regions.pdf exactly) -->
  <div class="px-6 pb-12">
    <div class="section-title font-semibold mb-2">UN Regional Summaries</div>
    <p class="text-sm text-slate-400 max-w-2xl mb-6">The blocks below contain the complete regional summaries (identical data to the print RTLDI_ATLAS_2026_regions.pdf). Each shows the current level of the nine RTLDI levers and the volume of capital exclusions in that region — the lost potential GDP that is sitting outside the economy because the protections required for capital to operate are not present. The focus is on making the scale of excluded capital visible so it can be brought back in.</p>
    {region_summaries_html}
  </div>

  {site_footer()}
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

    const el = document.createElement('a');
    el.href = `levers.html#lever-${{i + 1}}`;
    el.setAttribute('aria-label', `Open lever ${{i + 1}}: ${{name}}`);
    el.className = 'bg-white border border-slate-200 p-3 flex gap-3 items-center no-underline text-inherit hover:border-teal-600';
    el.innerHTML = `
      <div class="flex-1 min-w-0">
        <div class="flex justify-between text-xs">
          <div class="font-medium truncate pr-2">${{name}}</div>
          <div class="tabular-nums text-teal-700 font-medium">${{(lost/1e9).toFixed(1)}}B</div>
        </div>
        <div class="mt-1.5 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-2 bg-teal-700" style="width:${{w}}%"></div>
        </div>
      </div>
      <div class="text-[10px] text-slate-400 w-9 text-right tabular-nums">${{pct.toFixed(0)}}%</div>
    `;
    container.appendChild(el);
  }}
}}

// ================== REGION EXPLORER (maps are local SVGs, everything else JS) ==================
let currentRegion = null;

// Region summaries are now statically published in the HTML for fidelity to regions.pdf.

// ================== BOOT ==================
function boot() {{
  initTailwind();
  try {{
    renderGlobalBars();
  }} catch (error) {{
    console.error('[RTLDI HTML Atlas] Interactive controls failed to initialize:', error);
  }}
  console.log('%c[RTLDI HTML Atlas] Self-contained front+regions ready. Data matches print atlas.', 'color:#166534');
}}

document.addEventListener('DOMContentLoaded', boot);
</script>
{THEME_RUNTIME_SCRIPT}
</body>
</html>
"""

    index_path = HTML_DIR / "index.html"
    index_path.write_text(html, encoding="utf-8")

    full_data_path = HTML_DIR / "full_data.html"
    full_data_path.write_text(build_full_data_html(), encoding="utf-8")
    for filename, page in {
        "levers.html": levers_html,
        "regression.html": regression_html,
        "vdem.html": vdem_html,
        "world_bank.html": world_bank_html,
        "about.html": about_html,
    }.items():
        (HTML_DIR / filename).write_text(page, encoding="utf-8")

    rdf_path = write_rdf_atlas(data, HTML_DIR / "rtldi_atlas_2026.rdf")

    # Also drop a tiny data.json for transparency / power users
    (HTML_DIR / "data.json").write_text(json.dumps({
        "global": embed_global,
        "regions": embed_regions,
        "nations": embed_nations
    }, indent=2), encoding="utf-8")

    print(f"\nHTML atlas written to: {index_path}")
    print(f"Full data view written to: {full_data_path}")
    print("Evidence and project pages written: levers.html, regression.html, vdem.html, world_bank.html, about.html")
    print(f"RDF/XML linked data written to: {rdf_path}")
    print(f"Vector maps (SVG): {MAPS_DIR} (global.svg + 22 regional *.svg)")
    print("Open outputs/html-atlas/index.html in a browser. The full data table is outputs/html-atlas/full_data.html.")
    return index_path

def main():
    print("Preparing data (reusing exact same capped 2026 numbers as the print atlas)...")
    data = prepare_atlas_data()
    build_html_atlas(data)
    print("Done.")

if __name__ == "__main__":
    main()
