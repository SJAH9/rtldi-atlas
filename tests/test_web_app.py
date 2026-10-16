import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from src.generate_web_app import APP_HEAD, PAGES, install_web_app


class WebAppTest(unittest.TestCase):
    def test_install_is_idempotent_and_preserves_page_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = '<!doctype html><html><head><title>Signal</title></head><body><main>Original data and equations</main></body></html>'
            for filename in PAGES:
                (root / filename).write_text(original)
            with contextlib.redirect_stdout(io.StringIO()):
                install_web_app(root)
                install_web_app(root)
            for filename in PAGES:
                html = (root / filename).read_text()
                self.assertEqual(html.count('<!-- RTLDI app frame -->'), 1)
                self.assertEqual(html.replace('\n' + APP_HEAD, ''), original)
            manifest = json.loads((root / 'manifest.webmanifest').read_text())
            self.assertEqual(manifest['scope'], './')
            self.assertEqual(manifest['start_url'], './app.html')
            self.assertEqual(manifest['display'], 'standalone')
            for icon in manifest['icons']:
                with Image.open(root / icon['src']) as image:
                    size = int(icon['sizes'].split('x')[0])
                    self.assertEqual(image.size, (size, size))
            for asset in ('app.css', 'app.js', 'sw.js', 'bootstrap.js', 'embedded.css', 'offline.html'):
                self.assertTrue((root / asset).is_file(), asset)

    def test_frame_has_one_header_footer_and_correct_pdf_destinations(self):
        html = (Path('src/web_app') / 'app.html').read_text()
        self.assertEqual(html.count('<header '), 1)
        self.assertEqual(html.count('<footer '), 1)
        self.assertIn('releases/download/v2026.8.8/RTLDI_EUROZONE_CAPITAL_EXCLUSION_MAP_2026.pdf', html)
        self.assertIn('allow="fullscreen"', html)


if __name__ == '__main__':
    unittest.main()
