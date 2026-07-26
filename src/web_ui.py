"""Shared navigation and automatic theme contract for RTLDI web outputs."""

from __future__ import annotations

from html import escape


THEME_BOOT_SCRIPT = """<script>
(function () {
  var now = new Date();
  var hour = now.getHours() + now.getMinutes() / 60;
  document.documentElement.dataset.theme = (hour < 7 || hour >= 19) ? 'night' : 'day';
})();
</script>"""


THEME_RUNTIME_SCRIPT = """<script>
(function () {
  function applyAtlasTheme() {
    var now = new Date();
    var hour = now.getHours() + now.getMinutes() / 60;
    var theme = (hour < 7 || hour >= 19) ? 'night' : 'day';
    var previous = document.documentElement.dataset.theme;
    document.documentElement.dataset.theme = theme;
    if (document.body) document.body.classList.toggle('night-mode', theme === 'night');
    if (previous !== theme) {
      window.dispatchEvent(new CustomEvent('rtldi-theme-change', {detail: {theme: theme}}));
    }
  }
  applyAtlasTheme();
  window.setInterval(applyAtlasTheme, 60 * 1000);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) applyAtlasTheme();
  });
})();
</script>"""


SITE_CHROME_CSS = """
  :root {
    --site-bg: #eef2f5;
    --site-surface: #ffffff;
    --site-surface-soft: #f5f8fa;
    --site-ink: #18202b;
    --site-muted: #5b6770;
    --site-rule: #c6d1da;
    --site-accent: #107e65;
    --site-accent-strong: #0b6754;
    color-scheme: light;
  }
  html[data-theme="night"] {
    --site-bg: #08111f;
    --site-surface: #111827;
    --site-surface-soft: #0f172a;
    --site-ink: #e5edf7;
    --site-muted: #9aa9bb;
    --site-rule: #334155;
    --site-accent: #2dd4bf;
    --site-accent-strong: #5eead4;
    color-scheme: dark;
  }
  html { background: var(--site-bg); }
  body { background: var(--site-bg); color: var(--site-ink); }
  .site-shell { background: var(--site-surface); color: var(--site-ink); }
  .site-header {
    position: sticky;
    inset-block-start: 0;
    z-index: 100;
    width: 100%;
    display: block;
    padding: 0;
    border: 0;
    border-bottom: 1px solid var(--site-rule);
    background: color-mix(in srgb, var(--site-surface) 96%, transparent);
    backdrop-filter: blur(12px);
  }
  .site-header-inner {
    min-height: 66px;
    padding: 10px 24px;
    display: grid;
    grid-template-columns: minmax(190px, auto) 1fr;
    align-items: center;
    gap: 24px;
  }
  .site-brand {
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 11px;
    color: var(--site-ink);
    text-decoration: none;
  }
  .site-brand-mark {
    flex: 0 0 36px;
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    background: var(--site-accent);
    color: #fff;
    font-size: 21px;
    font-weight: 750;
  }
  .site-brand-copy { min-width: 0; }
  .site-brand-name {
    display: block;
    font-size: 16px;
    line-height: 1.15;
    font-weight: 720;
    white-space: nowrap;
  }
  .site-page-label {
    display: block;
    margin-top: 3px;
    color: var(--site-muted);
    font-size: 12px;
    line-height: 1.15;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 260px;
  }
  .site-primary-nav {
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 3px;
  }
  .site-nav-link {
    min-height: 38px;
    padding: 8px 10px;
    border: 0;
    border-bottom: 2px solid transparent;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--site-muted);
    background: transparent;
    text-decoration: none;
    font-size: 14px;
    font-weight: 590;
    white-space: nowrap;
  }
  .site-nav-link:hover {
    color: var(--site-ink);
    background: var(--site-surface-soft);
  }
  .site-nav-link[aria-current="page"] {
    color: var(--site-accent-strong);
    border-bottom-color: var(--site-accent);
  }
  .site-nav-link.site-print-link {
    margin-left: 5px;
    border: 1px solid var(--site-rule);
    border-bottom-width: 1px;
    color: var(--site-ink);
  }
  .site-mobile-menu { display: none; }
  .site-context-nav {
    min-height: 44px;
    padding: 0 24px;
    border-bottom: 1px solid var(--site-rule);
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    background: var(--site-surface-soft);
    scrollbar-width: thin;
  }
  .site-context-label {
    margin-right: 5px;
    color: var(--site-muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .site-context-link {
    padding: 6px 9px;
    border: 1px solid transparent;
    color: var(--site-muted);
    text-decoration: none;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
  }
  .site-context-link:hover {
    color: var(--site-ink);
    border-color: var(--site-rule);
    background: var(--site-surface);
  }
  .site-context-link[aria-current="page"] {
    color: var(--site-accent-strong);
    border-color: var(--site-rule);
    background: var(--site-surface);
  }
  .site-footer {
    padding: 24px;
    border-top: 1px solid var(--site-rule);
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    color: var(--site-muted);
    background: var(--site-surface-soft);
    font-size: 13px;
    line-height: 1.5;
  }
  .site-footer-credit { max-width: 720px; }
  .site-footer strong { color: var(--site-ink); }
  .site-footer-links {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px 14px;
  }
  .site-footer a {
    color: var(--site-accent-strong);
    text-decoration: none;
  }
  .site-footer a:hover {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  html[data-theme="night"] .site-shell,
  html[data-theme="night"] .shell,
  html[data-theme="night"] .max-w-screen-xl {
    background: var(--site-surface) !important;
  }
  html[data-theme="night"] code {
    background: #1e293b;
    color: #dbeafe;
  }
  @media (max-width: 980px) {
    .site-header-inner {
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 10px 16px;
    }
    .site-primary-nav { display: none; }
    .site-mobile-menu {
      position: relative;
      display: block;
    }
    .site-mobile-menu summary {
      min-width: 74px;
      min-height: 38px;
      padding: 8px 11px;
      border: 1px solid var(--site-rule);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--site-ink);
      background: var(--site-surface);
      cursor: pointer;
      font-size: 14px;
      font-weight: 650;
      list-style: none;
    }
    .site-mobile-menu summary::-webkit-details-marker { display: none; }
    .site-mobile-menu[open] summary {
      border-color: var(--site-accent);
      color: var(--site-accent-strong);
    }
    .site-mobile-links {
      position: absolute;
      inset-block-start: calc(100% + 8px);
      inset-inline-end: 0;
      width: min(290px, calc(100vw - 32px));
      padding: 8px;
      border: 1px solid var(--site-rule);
      background: var(--site-surface);
      box-shadow: 0 14px 36px rgba(15, 23, 42, .18);
      display: grid;
      gap: 2px;
    }
    .site-mobile-links .site-nav-link {
      width: 100%;
      justify-content: flex-start;
      border: 0;
    }
    .site-mobile-links .site-nav-link[aria-current="page"] {
      background: var(--site-surface-soft);
      box-shadow: inset 3px 0 0 var(--site-accent);
    }
    .site-mobile-links .site-print-link { margin: 5px 0 0; }
    .site-context-nav { padding-inline: 16px; }
    .site-footer {
      padding: 22px 16px;
      flex-direction: column;
      gap: 14px;
    }
    .site-footer-links { justify-content: flex-start; }
  }
  @media (max-width: 520px) {
    .site-page-label { max-width: 190px; }
    .site-brand-name { font-size: 15px; }
  }
"""


_PRIMARY_LINKS = (
    ("overview", "Overview", "index.html"),
    ("map", "Map", "global_interactive.html"),
    ("data", "Full Data", "full_data.html"),
    ("levers", "Levers", "levers.html"),
    ("regression", "Regression", "regression.html"),
    ("sources", "Sources", "vdem.html"),
    ("about", "About", "about.html"),
)


def _link(href: str, label: str, key: str, active: str, extra: str = "") -> str:
    current = ' aria-current="page"' if key == active else ""
    classes = "site-nav-link" + (f" {extra}" if extra else "")
    return f'<a class="{classes}" href="{escape(href)}"{current}>{escape(label)}</a>'


def site_header(
    active: str,
    page_label: str,
    *,
    prefix: str = "",
    pdf_href: str = "../atlas/RTLDI_ATLAS_2026_ebook.pdf?v=2026.8.5",
) -> str:
    primary_active = "sources" if active in {"vdem", "world_bank"} else active
    links = "".join(
        _link(prefix + href, label, key, primary_active)
        for key, label, href in _PRIMARY_LINKS
    )
    print_link = _link(pdf_href, "Print Atlas", "print", active, "site-print-link")
    return f"""<header class="site-header">
  <div class="site-header-inner">
    <a class="site-brand" href="{escape(prefix + 'index.html')}">
      <span class="site-brand-mark" aria-hidden="true">R</span>
      <span class="site-brand-copy">
        <span class="site-brand-name">RTLDI ATLAS 2026</span>
        <span class="site-page-label">{escape(page_label)}</span>
      </span>
    </a>
    <nav class="site-primary-nav" aria-label="Primary">{links}{print_link}</nav>
    <details class="site-mobile-menu">
      <summary>Menu</summary>
      <nav class="site-mobile-links" aria-label="Primary mobile">{links}{print_link}</nav>
    </details>
  </div>
</header>"""


def site_footer(*, prefix: str = "") -> str:
    return f"""<footer class="site-footer">
  <div class="site-footer-credit"><strong><a href="{escape(prefix + 'about.html')}">RTLDI Atlas Project</a></strong><br>Open-source atlas, data pipeline, and generated outputs released under the MIT License.</div>
  <nav class="site-footer-links" aria-label="Project information">
    <a href="{escape(prefix + 'about.html')}">About &amp; citation</a>
    <a href="https://github.com/SJAH9/rtldi-atlas">GitHub repository</a>
  </nav>
</footer>"""


def context_nav(active: str, *, prefix: str = "") -> str:
    if active in {"map", "data"}:
        label = "Explore"
        links = (("map", "Interactive Map", "global_interactive.html"), ("data", "Full Data View", "full_data.html"))
    elif active in {"levers", "regression", "vdem", "world_bank"}:
        label = "Methods & Sources"
        links = (
            ("levers", "Nine Levers", "levers.html"),
            ("regression", "Regression & Eta", "regression.html"),
            ("vdem", "V-Dem", "vdem.html"),
            ("world_bank", "World Bank", "world_bank.html"),
        )
    else:
        return ""
    rendered = "".join(
        f'<a class="site-context-link" href="{escape(prefix + href)}"'
        f'{" aria-current=\"page\"" if key == active else ""}>{escape(text)}</a>'
        for key, text, href in links
    )
    return f'<nav class="site-context-nav" aria-label="{escape(label)}"><span class="site-context-label">{escape(label)}</span>{rendered}</nav>'
