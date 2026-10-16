"""Install the common web-app frame without recalculating Atlas data."""

from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont

SOURCE = Path(__file__).parent / 'web_app'
DESTINATION = Path('outputs/html-atlas')
PAGES = ('index.html', 'global_interactive.html', 'full_data.html', 'levers.html',
         'regression.html', 'vdem.html', 'world_bank.html', 'about.html')
APP_HEAD = '''<!-- RTLDI app frame -->
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#16755f">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="apple-touch-icon" href="assets/icon-180.png">
<link rel="icon" href="assets/icon-192.png" type="image/png">
<link rel="stylesheet" href="embedded.css">
<script src="bootstrap.js"></script>
'''


def install_web_app(destination: Path = DESTINATION) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, dirs_exist_ok=True)
    fonts = [Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
             Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]
    font_path = next((path for path in fonts if path.exists()), None)
    if font_path is None:
        raise RuntimeError('A scalable Arial or DejaVu Sans font is required for app icons')
    for name, size, maskable in [('icon-180.png', 180, False), ('icon-192.png', 192, False),
                                 ('icon-512.png', 512, False), ('icon-maskable-512.png', 512, True)]:
        icon = Image.new('RGB', (size, size), '#16755f')
        draw = ImageDraw.Draw(icon)
        font = ImageFont.truetype(str(font_path), int(size * (0.55 if maskable else 0.68)))
        draw.text((size / 2, size / 2), 'R', font=font, fill='white', anchor='mm')
        icon.save(destination / 'assets' / name)
    for filename in PAGES:
        path = destination / filename
        if not path.exists():
            continue
        html = path.read_text(encoding='utf-8')
        html = html.replace('<meta name="theme-color" content="#107e65">', '<meta name="theme-color" content="#16755f">')
        if '<!-- RTLDI app frame -->' not in html:
            html = html.replace('<head>', '<head>\n' + APP_HEAD, 1)
        path.write_text(html, encoding='utf-8')
    print(f'Installable web-app frame written to {destination / "app.html"}')


if __name__ == '__main__':
    install_web_app()
