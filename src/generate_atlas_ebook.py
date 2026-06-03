#!/usr/bin/env python3
"""
Generate a print-ready PDF ebook for the RTLDI ATLAS 2026.

Structure:
- Title / cover page
- Executive description / foreword
- Methodology (condensed)
- Table of Contents
- Summary Table of All 193 UN Member Nations (paginated, sorted by total loss)
- Detailed profiles: one page per nation (A-Z order), with GDP loss projections + full 9-indicator RTLP breakdown + three-year RTLDI trend plot (varying G0, R fixed)
- Data Attribution & Sources
- Index of Terms
- Credits

Usage:
  python3 -m src.generate_atlas_ebook
  # or python src/generate_atlas_ebook.py

Outputs: outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import json
from pathlib import Path
import math
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any

# Optional matplotlib for the per-nation 3-year RTLDI (GDP) trend plots
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

try:
    import plotly.express as px
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# Page setup (A4 for print ebook, good margins)
PAGE_WIDTH = 210
PAGE_HEIGHT = 297
MARGIN = 15  # mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Font (Unicode capable on macOS)
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_NAME = "ArialUnicode"

# Colors
HEADER_COLOR = (31, 78, 121)  # dark blue
YES_COLOR = (0, 128, 0)
NO_COLOR = (180, 0, 0)
LIGHT_GRAY = (240, 240, 240)
BLACK = (0, 0, 0)

class RTLDIAtlasPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.add_font(FONT_NAME, "", FONT_PATH)
        self.add_font(FONT_NAME, "B", FONT_PATH)  # reuse for bold, fpdf2 will fake or use same
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.page_count_for_toc = 0  # not used in v1

    def header(self):
        if self.page_no() > 1:
            self.set_font(FONT_NAME, "", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, "RTLDI ATLAS 2026 | Right-to-Life Deficit Index for UN Member States", align="C")
            self.ln(4)
            self.set_draw_color(*HEADER_COLOR)
            self.line(MARGIN, 12, PAGE_WIDTH - MARGIN, 12)
            self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font(FONT_NAME, "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()} | Based on Sid J.A. Hubbard, Causality and Attraction v3 (DOI 10.5281/zenodo.19468550) | Data: V-Dem 2024 + World Bank (2026 baseline)", align="C")

    def chapter_title(self, title):
        self.set_font(FONT_NAME, "", 14)
        self.set_text_color(*HEADER_COLOR)
        self.multi_cell(0, 7, title, align="L")
        self.ln(2)
        self.set_draw_color(*HEADER_COLOR)
        self.line(MARGIN, self.get_y(), PAGE_WIDTH - MARGIN, self.get_y())
        self.ln(4)

    def body_text(self, text, size=10):
        self.set_font(FONT_NAME, "", size)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def small_text(self, text):
        self.set_font(FONT_NAME, "", 8)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 4, text)
        self.ln(1)

def load_detailed_data():
    path = Path("data/processed/rtl_di_nation_breakdown_2026.json")
    with open(path) as f:
        data = json.load(f)
    # Sort alpha for profiles
    data_sorted = sorted(data, key=lambda x: x["country"])
    return data, data_sorted


def load_g0_series(iso3_list, years=(2023, 2024, 2025)):
    """Load 3 years of G0 (GDP per capita current US$) for the given ISO3s.
    Prefers local WB bulk CSV (if present, as used by build_atlas), falls back to wbgapi.
    Returns dict iso3 -> {year: g0_value or None}
    """
    iso3s = {i.upper() for i in iso3_list}
    g0s = {iso: {y: None for y in years} for iso in iso3s}
    bulk = Path("data/raw/wb_gdp/API_NY.GDP.PCAP.CD_DS2_en_csv_v2_46.csv")
    has_bulk_data = False
    if bulk.exists():
        try:
            df = pd.read_csv(bulk, skiprows=4)
            df["iso3"] = df["Country Code"].astype(str).str.upper()
            for y in years:
                col = str(y)
                if col in df.columns:
                    sub = df[df["iso3"].isin(iso3s)][["iso3", col]].dropna(subset=[col])
                    for _, r in sub.iterrows():
                        g0s[r["iso3"]][y] = float(r[col])
                    has_bulk_data = True
            if has_bulk_data:
                print("  3yr G0: loaded from local bulk")
                return g0s
        except Exception as e:
            print(f"  3yr G0 bulk load failed ({e}), trying wbgapi...")
    # Fallback to live API (requires wbgapi; already used in core pipeline)
    try:
        import wbgapi as wb
        # numericTimeKeys for int years
        df = wb.data.DataFrame("NY.GDP.PCAP.CD", list(iso3s), time=list(years), labels=False, numericTimeKeys=True)
        df = df.reset_index().rename(columns={"index": "iso3"})
        df["iso3"] = df["iso3"].astype(str).str.upper()
        for y in years:
            if y in df.columns:
                sub = df[df["iso3"].isin(iso3s)][["iso3", y]].dropna(subset=[y])
                for _, r in sub.iterrows():
                    g0s[r["iso3"]][y] = float(r[y])
        print("  3yr G0: loaded via wbgapi fallback")
    except Exception as e:
        print(f"  3yr G0 wbgapi failed ({e}); trends will be partial/missing for some nations.")
    return g0s


def get_trend_plot_path(iso3: str, country: str, r: float, population: float, g0_by_year: dict,
                        years=(2023, 2024, 2025)) -> Optional[Path]:
    """Generate (or return cached temp) small PNG trend plot for this nation's RTLDI over 3 G0 years.
    Uses fixed R + pop from the 2026 atlas; varies only G0. Returns path or None if insufficient data.
    """
    if not HAS_MPL:
        return None
    # Write to outputs (gitignored by outputs/figures/* rule) so user can inspect the per-nation trend plots after build
    outdir = Path("outputs/figures/rtl_di_trends_2026")
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{iso3}.png"
    # Always (re)build for freshness during this run; cheap
    xs, ys_tot, ys_pc = [], [], []
    for y in years:
        g0 = g0_by_year.get(y)
        if g0 is None or (isinstance(g0, float) and np.isnan(g0)):
            continue
        if r is None or population is None or population <= 0:
            continue
        try:
            dg = 0.05 * (1.0 - float(r)) * float(g0)
            tot_b = dg * float(population) / 1e9
            xs.append(int(y))
            ys_tot.append(tot_b)
            ys_pc.append(dg)
        except Exception:
            continue
    if len(xs) < 2:
        return None
    fig, ax = plt.subplots(figsize=(5.2, 1.7), dpi=100)
    c = "#1F4E79"
    ax.plot(xs, ys_tot, "-o", color=c, lw=1.1, ms=3.5)
    ax.fill_between(xs, ys_tot, alpha=0.12, color=c)
    short = (country[:22] + "…") if len(country) > 23 else country
    ax.set_title(f"RTLDI Deficit Trend — {short} (R={r:.2f} fixed)", fontsize=6.5, pad=1)
    ax.set_ylabel("Total annual loss\n(USD billions)", fontsize=5.5)
    ax.set_xlabel("Year (G₀)", fontsize=5.5)
    ax.tick_params(axis="both", labelsize=5)
    for x, y, pc in zip(xs, ys_tot, ys_pc):
        ax.annotate(f"${pc:,.0f}", xy=(x, y), xytext=(0, 3), textcoords="offset points",
                    fontsize=4.2, ha="center", color="#333")
    ax.grid(True, ls=":", alpha=0.35)
    plt.tight_layout(pad=0.2)
    fig.savefig(p, dpi=100, facecolor="white", edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    return p


def get_nation_focus_map(iso3: str, country: str, un_region: Optional[str], all_nations: list) -> Optional[Path]:
    """Generate a small 'zoomed' choropleth for this nation + others in its UN region (proxy for geographic neighbors/context).
    Uses the same Viridis R scale as the global map. Cached in outputs/figures/nation_focus_maps/
    """
    if not HAS_PLOTLY:
        return None
    out_dir = Path("outputs/figures/nation_focus_maps")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{iso3}_focus.png"
    if p.exists():
        return p

    # Focus set: the target country + all others in the same UN region (reasonable "neighborhood" proxy)
    region = un_region or ""
    focus = [n for n in all_nations if (n.get("un_region") or "") == region or n["iso3"] == iso3]
    if len(focus) < 2:
        focus = [n for n in all_nations if n["iso3"] == iso3]

    focus_df = pd.DataFrame([
        {"iso3": n["iso3"], "r": float(n.get("r", 0.0)), "country": n.get("country", n["iso3"])}
        for n in focus
    ])

    fig = px.choropleth(
        focus_df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale="Viridis",
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={"r": ":.3f"},
    )

    fig.update_geos(
        fitbounds="locations",
        showcoastlines=True,
        coastlinecolor="rgba(180,180,180,0.6)",
        showland=True,
        landcolor="rgba(245,245,245,0.9)",
        showocean=True,
        oceancolor="rgba(230,242,255,0.6)",
        projection_type="natural earth",
    )

    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="R", font=dict(size=7)),
            len=0.4,
            thickness=6,
        ),
        title=dict(text=f"{country} + region (enclosure strength R)", font=dict(size=8)),
        margin=dict(l=1, r=1, t=16, b=1),
        height=180,
        width=380,
        paper_bgcolor="white",
    )

    # Mark the target nation
    fig.add_annotation(
        text=f"★ {iso3}",
        x=0.5,
        y=0.92,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=6, color="#c00"),
        bgcolor="rgba(255,255,255,0.75)",
    )

    fig.write_image(p, width=380, height=180, scale=1.5)
    return p


def get_regional_choropleth(region_name: str, all_nations: list) -> Optional[Path]:
    """Generate a choropleth map for all countries in a UN region (zoomed to the region).
    Saved to outputs/figures/regional_choropleths/ (gitignored; regenerated on build).
    """
    if not HAS_PLOTLY or not region_name:
        return None
    out_dir = Path("outputs/figures/regional_choropleths")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = region_name.lower().replace(" ", "_").replace("/", "_").replace(",", "")
    p = out_dir / f"{slug}.png"
    if p.exists():
        return p
    focus = [n for n in all_nations if (n.get("un_region") or "") == region_name]
    if not focus:
        return None
    focus_df = pd.DataFrame([
        {"iso3": n["iso3"], "r": float(n.get("r", 0.0)), "country": n.get("country", n["iso3"])}
        for n in focus
    ])
    fig = px.choropleth(
        focus_df,
        locations="iso3",
        locationmode="ISO-3",
        color="r",
        color_continuous_scale="Viridis",
        range_color=[0.0, 1.0],
        hover_name="country",
        hover_data={"r": ":.3f"},
    )
    fig.update_geos(
        fitbounds="locations",
        showcoastlines=True,
        coastlinecolor="rgba(180,180,180,0.6)",
        showland=True,
        landcolor="rgba(245,245,245,0.9)",
        showocean=True,
        oceancolor="rgba(230,242,255,0.6)",
        projection_type="natural earth",
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="R", font=dict(size=7)),
            len=0.4,
            thickness=6,
        ),
        title=dict(text=f"{region_name} Region — Enclosure Strength (R)", font=dict(size=8)),
        margin=dict(l=1, r=1, t=14, b=1),
        height=200,
        width=400,
        paper_bgcolor="white",
    )
    fig.write_image(p, width=400, height=200, scale=1.5)
    return p


def create_pdf():
    pdf = RTLDIAtlasPDF()
    detailed_all, detailed_alpha = load_detailed_data()

    # Load 3 years G0 series for the per-nation RTLDI trend plots (GDP-driven, R fixed)
    print("Loading 3-year G0 series for nation trend plots...")
    all_isos = [d["iso3"] for d in detailed_all]
    g0_series = load_g0_series(all_isos)

    # Compute regional aggregates for UN Regional Summaries section (one page per UN region)
    print("Computing regional summaries for UN Regional Summaries (aggregates + 9-indicator breakdowns)...")
    from collections import defaultdict
    region_countries = defaultdict(list)
    for d in detailed_all:
        reg = d.get("un_region") or "Unknown"
        region_countries[reg].append(d)
    regional_data = {}
    for reg, cs in region_countries.items():
        n = len(cs)
        if n == 0:
            continue
        pops = [float(c.get("population") or 0) for c in cs]
        total_pop = sum(pops)
        rs = [float(c.get("r") or 0) for c in cs]
        mean_r = sum(rs) / n
        weighted_r = sum(r * p for r, p in zip(rs, pops)) / total_pop if total_pop > 0 else mean_r
        losts = [float(c.get("total_deficit_usd") or 0) for c in cs]
        total_lost = sum(losts)
        g0s = [float(c.get("g0") or 0) for c in cs]
        mean_g0 = sum(g0s) / n if n else 0
        # 9 indicators: frac Yes + attributable lost GDP
        inds = []
        if cs and "components" in cs[0]:
            for i in range(9):
                comps = [c["components"][i] for c in cs if "components" in c and len(c.get("components", [])) > i]
                if not comps:
                    continue
                bins = [int(comp.get("bin", 0)) for comp in comps]
                raws = [comp.get("raw") for comp in comps]
                n_yes = sum(bins)
                frac_yes = n_yes / len(bins) if bins else 0
                valid_raws = []
                for x in raws:
                    if x is not None:
                        try:
                            valid_raws.append(float(x))
                        except (ValueError, TypeError):
                            pass
                avg_raw = sum(valid_raws) / len(valid_raws) if valid_raws else 0
                # attributable: for bin==0 countries, add (0.05/9 * g0 * pop)
                attr_lost = 0.0
                for c in cs:
                    if "components" in c and len(c.get("components", [])) > i:
                        if int(c["components"][i].get("bin", 0)) == 0:
                            g0 = float(c.get("g0") or 0)
                            pop = float(c.get("population") or 0)
                            attr_lost += 0.05 * (1.0 / 9.0) * g0 * pop
                inds.append({
                    "num": i + 1,
                    "name": comps[0].get("name", ""),
                    "desc": comps[0].get("desc", ""),
                    "frac_yes": frac_yes,
                    "n_yes": n_yes,
                    "n_countries": len(bins),
                    "avg_raw": avg_raw,
                    "attributable_lost_gdp": attr_lost,
                })
        regional_data[reg] = {
            "n_countries": n,
            "total_pop": total_pop,
            "mean_r": mean_r,
            "weighted_r": weighted_r,
            "total_lost_gdp": total_lost,
            "mean_g0": mean_g0,
            "indicators": inds,
            "members": cs,  # full per-country dicts for the nations table on the region page
        }
    sorted_regions = sorted(regional_data.items(), key=lambda x: -x[1]["total_lost_gdp"])

    # Sort for summary table by total loss desc (highest impact first)
    detailed_by_loss = sorted(
        [d for d in detailed_all if d.get("total_deficit_usd")],
        key=lambda x: x["total_deficit_usd"],
        reverse=True
    )

    # ========== TITLE PAGE ==========
    pdf.add_page()
    pdf.set_font(FONT_NAME, "", 28)
    pdf.set_text_color(*HEADER_COLOR)
    pdf.ln(30)
    pdf.cell(0, 12, "RTLDI ATLAS 2026", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(FONT_NAME, "", 14)
    pdf.ln(5)
    pdf.cell(0, 8, "Right-to-Life Deficit Index", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "for United Nations Member States", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)
    pdf.set_font(FONT_NAME, "", 11)
    pdf.set_text_color(60,60,60)
    pdf.multi_cell(0, 6, "Projected Annual GDP Losses from Incomplete Protection\nof the Right to Life\n\n2026 Edition", align="C")
    pdf.ln(15)
    pdf.set_font(FONT_NAME, "", 9)
    pdf.multi_cell(0, 5, "Based on the framework in\nSid J.A. Hubbard\nCausality and Attraction: A Continuum of Steady States (Version 3, May 2026)\nDOI: 10.5281/zenodo.19468550", align="C")
    pdf.ln(10)
    pdf.set_font(FONT_NAME, "", 8)
    pdf.cell(0, 5, "Data: V-Dem (2024) + World Bank (latest GDP baseline as of 2026)", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, "Prepared for NGOs, researchers, and policymakers", align="C")

    # ========== EXECUTIVE DESCRIPTION ==========
    pdf.add_page()
    pdf.chapter_title("Executive Description")
    pdf.body_text(
        "The Right-to-Life Deficit Index (RTLDI) quantifies the annual economic cost, in lost GDP, "
        "that results when states fail to provide equal and effective protection of the right to life. "
        "It translates the nine binary indicators of Right-to-Life Protection (RTLP) — drawn from legal, "
        "judicial, enforcement, conflict, and socioeconomic realities — into a 0–1 score (R). "
        "The core equation, ΔG = 0.05 × (1 − R) × G₀, yields the per-capita GDP loss; multiplied by population "
        "it produces the aggregate national deficit.\n\n"
        "This 2026 Atlas applies the framework to all 193 UN Member States. V-Dem data (latest 2024) supplies "
        "the eight governance and civil-liberties components; World Bank data supplies the most recent published "
        "GDP per capita as the dynamic baseline (G₀) for 2026. The result is a transparent, reproducible map of "
        "where incomplete protection of life imposes the largest measurable drag on human economic activity."
    )
    pdf.ln(3)
    pdf.body_text(
        "The Atlas is intended as a practical reference for NGOs, national human-rights institutions, "
        "development agencies, researchers, and — most importantly — for the people and policymakers "
        "inside each of the 193 nations who want to understand the concrete economic costs of incomplete "
        "right-to-life protection and to use that knowledge as a diagnostic for reform.\n\n"
        "A dedicated Diagnostic Guide (following the Methodology) explains how to read the R scores and "
        "9-component breakdowns as levers: which policy choices and cultural norms move each indicator, "
        "how the resulting economic drag becomes visible and attributable, and how awareness of lost "
        "potential can shift incentives for the very indicators that are at cause."
    )

    # ========== METHODOLOGY ==========
    pdf.add_page()
    pdf.chapter_title("Methodology and Data Sources")
    pdf.body_text(
        "RTLP Score (R)\n"
        "R is the simple average of nine binary indicators (0 = no protection, 1 = full protection). "
        "Eight indicators are derived from V-Dem v15 (2024 data) using the following thresholds "
        "(higher = stronger protection):\n\n"
        "1. Legal Protections — v2cltrnslw ≥ 2.0\n"
        "2. Independent Judiciary — average(v2juhcind, v2juncind) ≥ 2.0\n"
        "3. Law Enforcement Accountability — v2clkill ≥ 2.0\n"
        "4. Protection Against Arbitrary Detention — v2xcl_acjst ≥ 0.5\n"
        "5. Freedom from Torture — v2cltort ≥ 2.0\n"
        "6. Civilian Protection in Conflict — v2clkill ≥ 2.0\n"
        "7. Access to Justice — v2xcl_acjst ≥ 0.5\n"
        "8. Freedom of Expression & Whistleblower Protections — v2x_freexp ≥ 0.5\n\n"
        "9. Socioeconomic Conditions — World Bank: undernourishment ≤ 5 % AND poverty headcount ($2.15) ≤ 10 %.\n\n"
        "R = (number of 'Yes' indicators) / 9\n\n"
        "Economic Projection\n"
        "ΔG (per-capita loss) = 0.05 × (1 − R) × G₀, where G₀ is the most recent published GDP per capita "
        "(World Bank, labeled 2026 baseline in this edition). Total national loss = ΔG × population.\n\n"
        "Data Vintage Note for 2026 Edition\n"
        "V-Dem components reflect the latest available year in the source file (2024). GDP per capita (G₀) "
        "uses the freshest published values available at the time of atlas production. This follows the "
        "principle that RTLP governance scores are relatively stable year-to-year while GDP is the more "
        "dynamic variable in the equation."
    )
    pdf.small_text(
        "Full crosswalk and binarization rules: docs/indicator_crosswalk.md\n"
        "Source equations: Sid J.A. Hubbard, Causality and Attraction v3 (2026), DOI 10.5281/zenodo.19468550"
    )

    # ========== DIAGNOSTIC GUIDE ==========
    pdf.add_page()
    pdf.chapter_title("Diagnostic Guide: Using RTLDI as a Reform Tool")

    pdf.body_text(
        "The RTLDI ATLAS is not only a ranking. It is a diagnostic instrument that converts the presence or absence of nine specific protections into a recurring, measurable annual economic cost.\n\n"
        "This section explains how people and policymakers inside these nations can use the R scores, the 9-component breakdowns, the per-capita ΔG figures, and the total national deficits as concrete levers for change."
    )

    pdf.chapter_title("The Core Translation")
    pdf.body_text(
        "The equation is ΔG = 0.05 × (1 − R) × G₀.\n\n"
        "R is the average of the nine binary RTLP indicators. G₀ is GDP per capita. ΔG is the estimated annual loss per person caused by incomplete protection of life. Total national deficit ≈ ΔG × population.\n\n"
        "A country with R = 0.44 and G₀ = $10,000 loses roughly $280 per person every year — money that never materializes in budgets, never circulates, never funds the next generation. When this number is large, persistent, and broken down into nine specific, fixable components, it stops being an abstract 'governance problem' and becomes a structural drag with a visible price tag."
    )

    pdf.chapter_title("The Nine Levers — What Actually Moves R")
    pdf.body_text(
        "R changes only when one or more indicators flip from 0 to 1. Each flip is worth ~0.11 in R and therefore ~0.55 % of G₀ in reduced annual per-capita loss for the whole population.\n\n"
        "1. Legal Protections (transparent, predictable enforcement that actually constrains power). Moved by consistent application of ordinary law against state agents, not by paper constitutions.\n\n"
        "2. Independent Judiciary. Moved by insulated appointments, secure tenure, and a professional culture that rewards fidelity to law over political advancement.\n\n"
        "3. Law Enforcement Accountability. Moved by independent investigations, data transparency, civilian oversight with power, and political leadership that refuses to incite or excuse unlawful killings.\n\n"
        "4. Protection Against Arbitrary Detention. Moved by real habeas, time limits on pre-trial detention, legal aid, and courts willing to order release of politically inconvenient people.\n\n"
        "5. Freedom from Torture. Moved by criminalization with no loopholes, exclusion of tainted evidence, monitoring of detention, and training that treats torture as career suicide.\n\n"
        "6. Civilian Protection in Conflict/High-Violence Areas. Moved by rules of engagement that enforce distinction and proportionality, effective command responsibility, and post-incident accountability even when victims are unpopular.\n\n"
        "7. Access to Justice. Moved by affordable legal aid for serious claims, protection for lawyers taking hard cases, timely proceedings, and enforcement of judgments against the state itself.\n\n"
        "8. Freedom of Expression & Whistleblower Protection. Moved by decriminalization of criticism, source protection, real whistleblower remedies, and a political culture that treats exposure of state violence as legitimate rather than disloyal.\n\n"
        "9. Socioeconomic Conditions (basic nutrition and health). Moved by fiscal priorities, social insurance design, land and labor policy, and the political decision to treat minimal life-sustaining conditions as a public responsibility rather than a private consumption choice.\n\n"
        "These nine are causally nested. Weak judicial independence undermines accountability for killings and torture. Weak expression rights make it harder for anyone to document the other failures. The source document frames them as structural parameters inside 'nested causal enclosures' that enable or constrain higher-order economic and social steady states."
    )

    pdf.chapter_title("How Awareness of Lost Economic Potential Changes the Indicators")
    pdf.body_text(
        "When the only available language is 'human rights are good,' the political costs of reform (upsetting security services, elites, or nationalist stories) usually prevail. The benefits remain moral and diffuse.\n\n"
        "When the same reform can also be described as 'this specific change would return roughly $X billion per year to our economy, every year, and here are the three statutes and one appointment that would flip the indicator,' the political economy shifts.\n\n"
        "Finance ministries acquire a stake. Business groups can be recruited. Opposition parties can campaign on stopping the waste. Media has a concrete number instead of another abstract abuse story. International partners can target assistance to the exact weak indicators rather than generic 'rule of law' programs.\n\n"
        "The 3-year trend plots on each nation page exist for this purpose: they show whether the drag is stable, growing with the economy even while R is flat, or beginning to shrink as specific protections improve."
    )

    pdf.chapter_title("Practical Use")
    pdf.body_text(
        "For national policymakers: Open your profile. Note your R and the specific 'No' indicators. Compare the total annual deficit to your health or education budget. Ask the civil service to cost the political and budgetary effort required to move one or two indicators in the next V-Dem cycle and compare it to the recurring benefit.\n\n"
        "For civil society and media: Use the numbers in domestic advocacy, not only international forums. 'We lose $2.3 billion every year because we have not made law enforcement accountable for killings. That is more than the entire health budget. Here is the one change that begins to close the gap.'\n\n"
        "For citizens: The data is public. When leaders promise 'development,' ask which of the nine protections they will strengthen and how we will know in four years whether R has moved.\n\n"
        "For international actors: Stop separating 'human rights' and 'economic growth' pillars. Target a share of governance and security assistance explicitly to the indicators that are currently 'No' for that country and measure success partly by movement on those variables in the next data release."
    )

    pdf.chapter_title("Limitations and Responsible Use")
    pdf.body_text(
        "R in this edition uses 2024 V-Dem data paired with the freshest published GDP figures. Real-time events after the data cutoff are not yet visible. Binarization thresholds are modeling choices; always examine the raw values in the nation breakdowns. The 0.05 coefficient is a central estimate; the identity of the weak indicators is more robust than the precise dollar figure. Causality runs both ways: low R produces drag, and severe economic stress can degrade state capacity and rights performance.\n\n"
        "The deeper claim, taken from the source document, is that these nine protections are not a moral add-on but structural parameters that make certain kinds of economic and social steady states easier or harder to reach. Making the cost of a weak parameter legible in annual GDP terms does not reduce rights to economics. It makes the causal structure visible to the actors who can actually adjust the parameters."
    )

    pdf.small_text(
        "Full version and updates: docs/diagnostic_guide.md\n"
        "Source framework: Sid J.A. Hubbard, Causality and Attraction v3 (2026), DOI 10.5281/zenodo.19468550"
    )

    # ========== TABLE OF CONTENTS ==========
    pdf.add_page()
    pdf.chapter_title("Table of Contents")
    pdf.set_font(FONT_NAME, "", 10)
    toc_items = [
        ("Executive Description", "2"),
        ("Methodology and Data Sources", "3"),
        ("Diagnostic Guide: Using RTLDI for Reform", "4"),
        ("Summary Table of All 193 UN Member Nations", "6"),
        ("UN Regional Summaries (22 regions)", "8"),
        ("Detailed Nation Profiles (A–Z)", "~30"),
        ("Data Attribution and Sources", "~210"),
        ("Index of Terms", "~211"),
        ("Credits and Acknowledgments", "~212"),
    ]
    for title, page in toc_items:
        pdf.cell(0, 6, f"{title}", border=0)
        pdf.cell(0, 6, page, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.small_text(
        "Note: Detailed profiles are ordered alphabetically by country name. "
        "The Summary Table is sorted by estimated total annual GDP loss (highest first). "
        "Exact page numbers for profiles depend on final layout; profiles begin after the summary tables."
    )

    # ========== SUMMARY TABLE OF ALL NATIONS ==========
    pdf.add_page()
    pdf.chapter_title("Summary Table of All 193 UN Member Nations")
    pdf.small_text(
        "Sorted by estimated total annual GDP loss (highest first). "
        "R = RTLP score (0–1); values shown as fraction of 9 indicators where possible. "
        "Losses in current USD using 2026 baseline GDP per capita paired with latest available RTLP components (2024)."
    )
    pdf.ln(2)

    # Table header
    col_widths = [8, 38, 22, 18, 22, 28, 28]  # rank, name, region, r, percap, total, pop
    headers = ["#", "Country", "Region", "R", "Per Capita Loss", "Total Loss (USD)", "Population"]
    pdf.set_font(FONT_NAME, "", 7)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 5, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*BLACK)
    pdf.set_font(FONT_NAME, "", 6.5)

    # Paginated table rows (simple, ~35 rows per page)
    rows_per_page = 38
    for idx, d in enumerate(detailed_by_loss):
        if idx > 0 and idx % rows_per_page == 0:
            pdf.add_page()
            # repeat header
            pdf.set_font(FONT_NAME, "", 7)
            pdf.set_fill_color(*HEADER_COLOR)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 5, h, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(*BLACK)
            pdf.set_font(FONT_NAME, "", 6.5)

        rank = int(d.get("rank_by_total_deficit", idx+1)) if d.get("rank_by_total_deficit") else idx+1
        country = d["country"][:28]
        region = d["un_region"][:18] if d.get("un_region") else ""
        r_val = d["r"]
        r_str = f"{r_val:.2f}" if r_val is not None else "N/A"
        per_cap = d["delta_g_per_capita"]
        per_cap_str = f"${per_cap:,.0f}" if per_cap is not None else "N/A"
        total = d["total_deficit_usd"]
        if total is not None:
            if total >= 1e9:
                total_str = f"${total/1e9:.1f} bn"
            else:
                total_str = f"${total/1e6:.0f} m"
        else:
            total_str = "N/A"
        pop = d["population"]
        pop_str = f"{pop/1e6:.1f} m" if pop is not None else "N/A"

        pdf.cell(col_widths[0], 4.2, str(rank), border=1, align="C")
        pdf.cell(col_widths[1], 4.2, country, border=1)
        pdf.cell(col_widths[2], 4.2, region, border=1)
        pdf.cell(col_widths[3], 4.2, r_str, border=1, align="C")
        pdf.cell(col_widths[4], 4.2, per_cap_str, border=1, align="R")
        pdf.cell(col_widths[5], 4.2, total_str, border=1, align="R")
        pdf.cell(col_widths[6], 4.2, pop_str, border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ========== UN REGIONAL SUMMARIES ==========
    pdf.add_page()
    pdf.chapter_title("UN Regional Summaries")
    pdf.body_text(
        "The 193 UN Member States are grouped into 22 geographic regions. Below are one-page overviews for each region, "
        "aggregating the RTLDI metrics. For each region we show a choropleth of enclosure strength (R) for its member "
        "countries (zoomed to the region using the same Viridis scale as the global map), key aggregates (population-weighted "
        "average R, total annual lost GDP), and a breakdown of the 9 RTLP indicators. The breakdown reports the percentage "
        "of countries in the region scoring 'Yes' on each indicator and the estimated portion of the region's total lost GDP "
        "attributable to shortfalls on that indicator (the sum, across countries lacking the protection, of 0.05/9 × G₀ × population)."
    )
    pdf.small_text(
        "Regional statistics are derived directly from the per-country 2026 atlas values. High-impact regions (by total lost GDP) are shown first."
    )

    for reg_name, reg_sum in sorted_regions:
        pdf.add_page()
        # Region header + stats
        pdf.set_font(FONT_NAME, "", 11)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 5, f"{reg_name} Region", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(FONT_NAME, "", 7)
        pdf.set_text_color(70, 70, 70)
        stats = (
            f"Countries: {reg_sum['n_countries']}  |  "
            f"Population: {reg_sum['total_pop']/1e6:,.1f} million  |  "
            f"Pop-weighted Avg R: {reg_sum['weighted_r']:.3f}  |  "
            f"Total Annual Lost GDP: ${reg_sum['total_lost_gdp']/1e9:,.2f} billion"
        )
        pdf.cell(0, 4, stats, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        # Choropleth for the region
        map_p = get_regional_choropleth(reg_name, detailed_all)
        if map_p and map_p.exists():
            pdf.set_font(FONT_NAME, "", 6.5)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3, "Regional Choropleth — Enclosure Strength (R)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            ym = pdf.get_y()
            pdf.image(str(map_p), x=MARGIN + 5, w=CONTENT_WIDTH - 10, h=32)
            pdf.set_y(ym + 33)
            pdf.set_font(FONT_NAME, "", 5)
            pdf.set_text_color(90, 90, 90)
            pdf.multi_cell(0, 2.3,
                "Zoomed to countries in this UN region (colored by their individual R; same scale as the global choropleth). "
                "★ would mark a specific nation in per-country views."
            )
            pdf.ln(0.5)

        # Table of nations in the region + totals row
        members = reg_sum.get("members", [])
        if members:
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3, "Member Nations (RTLP R, G0 per capita, Population, RTLD I total lost)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.3)
            tcols = [36, 9, 15, 16, 20]  # ~96mm wide, compact for 1-page fit
            thdrs = ["Country", "R", "G0 ($)", "Pop", "Lost ($)"]
            pdf.set_font(FONT_NAME, "", 4.5)
            pdf.set_fill_color(*HEADER_COLOR)
            pdf.set_text_color(255, 255, 255)
            for ii, hh in enumerate(thdrs):
                pdf.cell(tcols[ii], 2.6, hh, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_text_color(*BLACK)
            for m in members:
                cname = str(m.get("country") or m.get("iso3", ""))[:20]
                rr = m.get("r")
                rstr = f"{rr:.2f}" if rr is not None else "N/A"
                gg = m.get("g0")
                gstr = f"{gg:,.0f}" if gg is not None else "N/A"
                pp = m.get("population")
                pstr = f"{pp/1e6:.1f}m" if pp else "N/A"
                ll = m.get("total_deficit_usd")
                if ll is not None:
                    lstr = f"${ll/1e9:.2f}b" if ll >= 1e9 else f"${ll/1e6:.0f}m"
                else:
                    lstr = "N/A"
                pdf.set_font(FONT_NAME, "", 4.2)
                pdf.cell(tcols[0], 2.4, cname, border=1)
                pdf.cell(tcols[1], 2.4, rstr, border=1, align="C")
                pdf.cell(tcols[2], 2.4, gstr, border=1, align="R")
                pdf.cell(tcols[3], 2.4, pstr, border=1, align="R")
                pdf.cell(tcols[4], 2.4, lstr, border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            # Totals row
            pdf.set_font(FONT_NAME, "", 4.5)
            pdf.set_fill_color(200, 200, 200)
            pdf.set_text_color(*BLACK)
            totp = reg_sum["total_pop"]
            totl = reg_sum["total_lost_gdp"]
            totpstr = f"{totp/1e6:.1f}m"
            totlstr = f"${totl/1e9:.2f}b"
            wrstr = f"{reg_sum['weighted_r']:.2f}"
            pdf.cell(tcols[0], 2.6, "REGIONAL TOTAL", border=1, fill=True)
            pdf.cell(tcols[1], 2.6, wrstr, border=1, align="C", fill=True)
            pdf.cell(tcols[2], 2.6, "", border=1, fill=True)
            pdf.cell(tcols[3], 2.6, totpstr, border=1, align="R", fill=True)
            pdf.cell(tcols[4], 2.6, totlstr, border=1, align="R", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_fill_color(240, 240, 240)
            pdf.ln(0.8)

        # 9 indicators breakdown for region
        pdf.set_font(FONT_NAME, "", 6.5)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 3.5, "RTLP Indicator Breakdown for the Region", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.3)

        for ind in reg_sum.get("indicators", []):
            pct = ind["frac_yes"] * 100
            lost_b = ind.get("attributable_lost_gdp", 0) / 1e9
            pdf.set_font(FONT_NAME, "", 5.2)
            pdf.set_text_color(*BLACK)
            line = f"{ind['num']}. {ind['name']}: {pct:.0f}% Yes ({ind['n_yes']}/{ind['n_countries']}) | avg raw {ind['avg_raw']:.2f}"
            pdf.cell(0, 2.6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font(FONT_NAME, "", 4.8)
            pdf.set_text_color(70, 70, 70)
            pdf.set_x(MARGIN + 2)
            pdf.multi_cell(0, 2.2,
                f"Attributable lost GDP: ${lost_b:,.2f} billion ({(lost_b * 1e9 / reg_sum['total_lost_gdp'] * 100) if reg_sum['total_lost_gdp'] > 0 else 0:.0f}% of region total). {ind['desc']}"
            )
            pdf.set_x(MARGIN)

        pdf.ln(0.5)
        pdf.set_font(FONT_NAME, "", 4.8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 2.1,
            "Note: Weighted R is population-weighted mean of member countries' R. Attributable lost for an indicator = sum over countries with 'No' on that indicator of (0.05/9 × G₀ × pop). "
            "See individual nation profiles for country-level detail and 3-year trends. Full global choropleth appears in the front matter / outputs/figures/."
        )

    # ========== DETAILED PROFILES (A-Z) ==========
    pdf.add_page()
    pdf.chapter_title("Detailed Nation Profiles (Alphabetical)")

    for d in detailed_alpha:
        pdf.add_page()

        # Header block
        pdf.set_font(FONT_NAME, "", 13)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 7, f"{d['country']} ({d['iso3']})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(80,80,80)
        pdf.cell(0, 5, f"UN Region: {d.get('un_region', 'N/A')}  |  RTLP R = {d['r']:.3f} ({sum(c['bin'] for c in d['components'])}/9)  |  V-Dem year: {d['vdem_year']}  |  G0 year: {d['g0_year']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        # Economic impact box
        pdf.set_fill_color(245, 245, 245)
        pdf.set_draw_color(*HEADER_COLOR)
        pdf.rect(MARGIN, pdf.get_y(), CONTENT_WIDTH, 22, style="DF")
        y_start = pdf.get_y() + 1
        pdf.set_xy(MARGIN + 2, y_start)
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*BLACK)
        g0 = d.get('g0') or 0
        dpc = d.get('delta_g_per_capita') or 0
        tot = d.get('total_deficit_usd') or 0
        pop = d.get('population') or 0
        pdf.multi_cell(CONTENT_WIDTH - 4, 3.8,
            f"Economic Impact (2026 GDP baseline)\n"
            f"G0 (GDP per capita): ${g0:,.0f}   |   "
            f"Per-capita annual loss (ΔG): ${dpc:,.0f}\n"
            f"Total annual GDP loss: ${tot/1e9:,.2f} billion   |   "
            f"Population: {pop/1e6:,.1f} million"
        )
        pdf.set_y(y_start + 22)

        # ========== 3-YEAR RTLDI (GDP) TREND PLOT ==========
        # Inserted per request: small plot of RTLDI deficit using 3 years of G0 (R fixed from 2024 components)
        plot_path = get_trend_plot_path(
            d["iso3"], d["country"], d.get("r"), d.get("population"),
            g0_series.get(d["iso3"], {})
        )
        if plot_path and plot_path.exists():
            pdf.ln(1)
            pdf.set_font(FONT_NAME, "", 7)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3.5, "Three-Year RTLDI Trend (based on 3 years of GDP data)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y_plot = pdf.get_y()
            img_w = CONTENT_WIDTH - 8
            # Fixed height ~24-25mm keeps most profiles on 1 page; aspect preserved by generator
            pdf.image(str(plot_path), x=MARGIN + 4, w=img_w, h=24)
            pdf.set_y(y_plot + 25)
            pdf.set_font(FONT_NAME, "", 5.5)
            pdf.set_text_color(95, 95, 95)
            pdf.multi_cell(0, 2.6,
                "R fixed from 2024 V-Dem crosswalk + latest socio #9 (see breakdown); G₀ varies (WB NY.GDP.PCAP.CD); pop fixed at latest. "
                "ΔG = 0.05 × (1 − R) × G₀; total = ΔG × pop. Years: 2023/2024/2025 (data availability in source bulk/API)."
            )
            pdf.ln(1)

        # Regional focus choropleth: this nation + others in its UN region (practical proxy for bordering/neighboring states)
        focus_p = get_nation_focus_map(d["iso3"], d["country"], d.get("un_region"), detailed_all)
        if focus_p and focus_p.exists():
            pdf.ln(0.5)
            pdf.set_font(FONT_NAME, "", 6.5)
            pdf.set_text_color(*HEADER_COLOR)
            pdf.cell(0, 3, "Regional Zoom — Enclosure Strength (R): this nation + region", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            yf = pdf.get_y()
            pdf.image(str(focus_p), x=MARGIN + 8, w=CONTENT_WIDTH - 16, h=17)
            pdf.set_y(yf + 18)
            pdf.set_font(FONT_NAME, "", 5)
            pdf.set_text_color(95, 95, 95)
            pdf.multi_cell(0, 2.3,
                "Cropped/zoomed view using the same global choropleth data and Viridis scale. ★ = this nation. Region used as practical stand-in for immediate geographic neighbors."
            )
            pdf.ln(0.5)

        pdf.ln(1.5)
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 4, "RTLP Score Breakdown — 9 Indicators", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.5)

        # 9 indicators - clean block layout (compacted to fit + 3yr plot on one page)
        for c in d['components']:
            yes = c['yes']
            color = YES_COLOR if yes == "Yes" else NO_COLOR
            raw_str = str(c['raw'])[:50] if c['raw'] is not None else "N/A"
            pdf.set_text_color(*BLACK)
            pdf.set_font(FONT_NAME, "", 6)
            status = f"[{yes}]"
            pdf.set_text_color(*color)
            pdf.cell(0, 2.9, f"{c['num']}. {c['name']} {status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(80,80,80)
            pdf.set_font(FONT_NAME, "", 5.2)
            pdf.set_x(MARGIN + 3)
            pdf.multi_cell(0, 2.5, f"raw: {raw_str} — {c['desc']}")
            pdf.set_x(MARGIN)

        pdf.ln(0.5)
        pdf.set_font(FONT_NAME, "", 5.5)
        pdf.set_text_color(100,100,100)
        pdf.multi_cell(0, 2.8,
            "Note: [Yes] = contributes +1 to R. Raw = V-Dem/WB value (higher=stronger protection). Thresholds in Methodology. Partial coverage possible for some nations. "
            "See the Diagnostic Guide section for how to use your R and component scores as a reform diagnostic tool."
        )

    # ========== DATA ATTRIBUTION ==========
    pdf.add_page()
    pdf.chapter_title("Data Attribution and Sources")
    pdf.body_text(
        "Primary Data\n"
        "• V-Dem (Varieties of Democracy) Country-Year Full+Others, version 15 (2024 data release). "
        "Indicators used: v2cltrnslw, v2juhcind, v2juncind, v2clkill, v2cltort, v2xcl_acjst, v2x_freexp.\n"
        "• World Bank World Development Indicators (WDI) via API — GDP per capita (current US$), "
        "population, prevalence of undernourishment, and poverty headcount at $2.15 (2017 PPP). "
        "Values are the most recent published as of atlas production (labeled 2026 baseline).\n"
        "• United Nations Member States list (193 sovereign states) for country scope and ISO3 codes.\n\n"
        "Source Framework\n"
        "The RTLDI equation, the nine RTLP indicators, and the nested causal interpretation are taken from:\n"
        "Sid J.A. Hubbard, Causality and Attraction: A Continuum of Steady States (Version 3, May 2026), "
        "DOI: 10.5281/zenodo.19468550. The operational crosswalk and binarization thresholds used here "
        "are documented in docs/indicator_crosswalk.md of this project."
    )
    pdf.small_text(
        "This PDF was generated programmatically from the open RTLDI ATLAS toolkit. "
        "No proprietary or restricted data were used."
    )

    # ========== INDEX OF TERMS ==========
    pdf.add_page()
    pdf.chapter_title("Index of Terms")
    terms = [
        ("ΔG (delta G)", "Annual GDP per capita loss due to incomplete right-to-life protection. Core output of the RTLDI equation."),
        ("G₀ (G-zero)", "Baseline GDP per capita (World Bank, current US$). The 'current' economic size against which the deficit is measured."),
        ("R (RTLP score)", "Right-to-Life Protection score, 0–1. Average of nine binary indicators. 1 = full protection across all dimensions."),
        ("RTLDI", "Right-to-Life Deficit Index — the full framework and the per-country or global aggregate loss figure."),
        ("RTLP", "Right-to-Life Protection — the nine binary indicators that are averaged to produce R."),
        ("V-Dem", "Varieties of Democracy project. Supplies the expert-coded governance and civil liberties indicators for eight of the nine RTLP components."),
        ("Crosswalk", "The explicit mapping from the nine verbatim RTLP questions to observable V-Dem variables and World Bank statistics, with defined binarization thresholds."),
        ("2026-fresh G0", "The most recent published GDP per capita values used as the dynamic baseline for the 2026 edition (even when RTLP components are from 2024)."),
    ]
    pdf.set_font(FONT_NAME, "", 8)
    for term, definition in terms:
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.multi_cell(0, 4, term + ":")
        pdf.set_font(FONT_NAME, "", 8)
        pdf.set_text_color(*BLACK)
        pdf.set_x(MARGIN + 5)
        pdf.multi_cell(0, 4, definition)
        pdf.ln(1)
        pdf.set_x(MARGIN)

    # ========== CREDITS ==========
    pdf.add_page()
    pdf.chapter_title("Credits and Acknowledgments")
    pdf.body_text(
        "Conceptual Framework and Equations\n"
        "Sid J.A. Hubbard — author of Causality and Attraction: A Continuum of Steady States (v3, 2026). "
        "All rights to the RTLDI equations, the nine RTLP indicators, and the nested causal paradigm remain with the author.\n\n"
        "Data\n"
        "• V-Dem Institute (https://www.v-dem.net) — V-Dem Country-Year dataset v15.\n"
        "• World Bank Open Data (https://data.worldbank.org) — WDI via API.\n"
        "• United Nations — list of 193 Member States.\n\n"
        "Code and Atlas Production\n"
        "RTLDI ATLAS project (2026). The open-source toolkit, crosswalk implementation, data pipeline, "
        "and this PDF generator are provided to make the framework usable by NGOs and researchers.\n\n"
        "This work is released in the spirit of the original document: to map, with transparent data and "
        "reproducible math, the economic consequences of failing to protect the right to life equally."
    )
    pdf.ln(5)
    pdf.set_font(FONT_NAME, "", 8)
    pdf.set_text_color(100,100,100)
    pdf.multi_cell(0, 4,
        "For the full source code, 2026 data tables, and previous editions (2023, 2024), see the project repository. "
        "Users are encouraged to download the latest V-Dem and World Bank releases and re-run the pipeline for updated figures."
    )

    # Save
    out_path = Path("outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(out_path)
    print(f"PDF ebook written to: {out_path}")
    print(f"Total pages: {pdf.page_no()}")

if __name__ == "__main__":
    create_pdf()
