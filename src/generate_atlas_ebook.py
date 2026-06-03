#!/usr/bin/env python3
"""
Generate a print-ready PDF ebook for the RTLDI ATLAS 2026.

Structure:
- Title / cover page
- Executive description / foreword
- Methodology (condensed)
- Table of Contents
- Summary Table of All 193 UN Member Nations (paginated, sorted by total loss)
- Detailed profiles: one page per nation (A-Z order), with GDP loss projections + full 9-indicator RTLP breakdown
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

def create_pdf():
    pdf = RTLDIAtlasPDF()
    detailed_all, detailed_alpha = load_detailed_data()

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
        "development agencies, and researchers who need country-level numbers grounded in the published "
        "equations and the best available open data."
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

    # ========== TABLE OF CONTENTS ==========
    pdf.add_page()
    pdf.chapter_title("Table of Contents")
    pdf.set_font(FONT_NAME, "", 10)
    toc_items = [
        ("Executive Description", "2"),
        ("Methodology and Data Sources", "3"),
        ("Summary Table of All 193 UN Member Nations", "4"),
        ("Detailed Nation Profiles (A–Z)", "8"),
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

        pdf.ln(3)
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 5, "RTLP Score Breakdown — 9 Indicators", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

        # 9 indicators - clean block layout
        for c in d['components']:
            yes = c['yes']
            color = YES_COLOR if yes == "Yes" else NO_COLOR
            raw_str = str(c['raw'])[:55] if c['raw'] is not None else "N/A"
            pdf.set_text_color(*BLACK)
            pdf.set_font(FONT_NAME, "", 7.5)
            status = f"[{yes}]"
            pdf.set_text_color(*color)
            pdf.cell(0, 3.6, f"{c['num']}. {c['name']} {status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(80,80,80)
            pdf.set_font(FONT_NAME, "", 6.5)
            pdf.set_x(MARGIN + 4)
            pdf.multi_cell(0, 3.2, f"raw: {raw_str}  —  {c['desc']}")
            pdf.set_x(MARGIN)

        pdf.ln(1)
        pdf.set_font(FONT_NAME, "", 7)
        pdf.set_text_color(100,100,100)
        pdf.multi_cell(0, 3.5,
            "Note: [Yes] means the binarized indicator contributes +1 to the RTLP score R. "
            "Raw values are the underlying V-Dem interval scores (higher = stronger protection) or World Bank percentages. "
            "Thresholds are documented in the Methodology section. Some countries have partial V-Dem coverage."
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
