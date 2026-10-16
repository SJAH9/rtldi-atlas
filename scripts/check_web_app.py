"""Browser checks for the Atlas frame. Requires Playwright and Chromium."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8767/outputs/html-atlas/')
    parser.add_argument('--browser', default='/Users/user/Library/Caches/ms-playwright/chromium-1228/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')
    parser.add_argument('--screenshots', default='/tmp/rtldi-web-app')
    args = parser.parse_args()
    screenshots = Path(args.screenshots)
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, ignore_https_errors=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url + 'index.html', wait_until='domcontentloaded')
        page.wait_for_url('**/app.html*')
        frame = page.frame_locator('#atlas-view')
        frame.locator('.site-shell').wait_for()
        page.screenshot(path=str(screenshots / 'desktop-overview.png'))
        assert page.locator('.atlas-header').count() == 1
        assert frame.locator('.site-header').evaluate('(el) => getComputedStyle(el).display') == 'none'
        assert frame.locator('h1').inner_text() == 'Overview'
        assert frame.locator('.atlas-overview-metric').count() == 4
        assert frame.locator('h1').evaluate('(el) => getComputedStyle(el).fontSize') == '26px'
        assert frame.locator('body').evaluate('(el) => getComputedStyle(el).backgroundColor') == page.locator('.atlas-header').evaluate('(el) => getComputedStyle(el).backgroundColor')
        assert page.locator('.atlas-header').bounding_box()['height'] <= 34
        assert page.locator('.atlas-footer').bounding_box()['height'] <= 26
        frame.locator('body').evaluate('(el) => el.dataset.stateCheck = "preserved"')
        frame.locator('body').evaluate('() => scrollTo(0, 100)')
        scroll = frame.locator('body').evaluate('() => scrollY')
        page.locator('#atlas-fullscreen').click()
        page.wait_for_function('Boolean(document.fullscreenElement)')
        assert frame.locator('body').get_attribute('data-state-check') == 'preserved'
        assert frame.locator('body').evaluate('() => scrollY') == scroll
        assert page.locator('#atlas-navigation a').all_text_contents() == ['Overview', 'Map', 'Full Data', 'About']
        page.locator('#atlas-sources').click()
        page.locator('#atlas-source-links a[data-view="levers.html"]').click()
        frame.locator('h1').filter(has_text='Levers').wait_for()
        assert not page.locator('#atlas-source-links').is_visible()
        assert page.locator('#atlas-sources').get_attribute('data-active') == 'true'
        assert page.evaluate('Boolean(document.fullscreenElement)')
        page.locator('#atlas-sources').click()
        page.locator('#atlas-source-links a[data-view="regression.html"]').click()
        page.wait_for_url('**app.html?view=regression.html')
        frame.locator('h1').wait_for()
        page.locator('#atlas-sources').click()
        page.locator('#atlas-source-links a[data-view="vdem.html"]').click()
        frame.locator('.site-context-link[href="world_bank.html"]').click()
        page.wait_for_url('**app.html?view=world_bank.html')
        frame.locator('h1').filter(has_text='World Bank').wait_for()
        page.go_back()
        page.wait_for_url('**app.html?view=vdem.html')
        frame.locator('h1').filter(has_text='V-Dem').wait_for()
        assert page.evaluate('Boolean(document.fullscreenElement)')
        page.locator('#atlas-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        page.locator('#atlas-navigation a[data-view="full_data.html"]').click()
        frame.locator('tbody tr').first.wait_for()
        assert frame.locator('tbody tr').count() >= 193
        page.screenshot(path=str(screenshots / 'desktop-data.png'))
        page.goto(args.url + 'global_interactive.html?country=SOM')
        page.wait_for_url('**app.html?view=*')
        frame.locator('#country-panel').filter(has_text='Somalia').wait_for(timeout=45000)
        frame.locator('#rtldi-map .main-svg').first.wait_for(timeout=45000)
        frame.locator('#rtldi-map').scroll_into_view_if_needed()
        assert frame.locator('#rtldi-map .choroplethlayer path').count() >= 190
        assert frame.locator('#auto-rotate-toggle').count() == 0
        page.wait_for_timeout(1200)
        page.screenshot(path=str(screenshots / 'desktop-map.png'))
        manifest = context.new_cdp_session(page).send('Page.getAppManifest')
        assert not manifest.get('errors'), manifest.get('errors')
        assert json.loads(manifest['data'])['display'] == 'standalone'
        page.evaluate("Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error('Service worker registration did not become ready')), 15000))])")
        page.wait_for_function('Boolean(navigator.serviceWorker.controller)')
        page.locator('#atlas-navigation a[data-view="about.html"]').click()
        frame.locator('h1').filter(has_text='About').wait_for()
        page.wait_for_function("caches.open('rtldi-atlas-app-v2').then(cache => cache.match(new URL('about.html', location.href).href)).then(Boolean)")
        context.set_offline(True)
        page.reload(wait_until='domcontentloaded')
        frame.locator('h1').filter(has_text='About').wait_for()
        page.screenshot(path=str(screenshots / 'desktop-offline.png'))
        context.set_offline(False)
        context.close()

        mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, ignore_https_errors=True)
        page = mobile.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url + 'app.html')
        page.frame_locator('#atlas-view').locator('.site-shell').wait_for()
        assert page.locator('#atlas-menu').is_visible()
        assert page.locator('#atlas-footer-menu').is_visible()
        page.locator('#atlas-footer-menu').click()
        assert page.locator('#atlas-project-links').is_visible()
        page.screenshot(path=str(screenshots / 'mobile-footer.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#atlas-menu').click()
        page.screenshot(path=str(screenshots / 'mobile-menu.png'))
        page.locator('#atlas-sources').click()
        assert not page.locator('#atlas-navigation').is_visible()
        page.screenshot(path=str(screenshots / 'mobile-sources.png'))
        page.locator('#atlas-source-links a[data-view="levers.html"]').click()
        page.frame_locator('#atlas-view').locator('h1').filter(has_text='Levers').wait_for()
        assert not page.locator('#atlas-navigation').is_visible()
        page.screenshot(path=str(screenshots / 'mobile-levers.png'))
        page.evaluate('''() => {
          const event = new Event('beforeinstallprompt', {cancelable: true});
          event.prompt = async () => { window.installRequested = true; };
          event.userChoice = Promise.resolve({outcome: 'accepted'});
          dispatchEvent(event);
        }''')
        page.locator('#atlas-install').click()
        assert page.evaluate('window.installRequested')
        assert not page.locator('#atlas-install').is_visible()
        page.set_viewport_size({'width': 320, 'height': 740})
        page.locator('#atlas-menu').click()
        page.locator('#atlas-navigation a[data-view="index.html"]').click()
        page.frame_locator('#atlas-view').locator('.stat').first.wait_for()
        assert page.frame_locator('#atlas-view').locator('.stat').first.evaluate('(el) => el.scrollWidth <= el.clientWidth')
        page.screenshot(path=str(screenshots / 'mobile-narrow.png'))
        day = browser.new_context(viewport={'width': 1280, 'height': 900}, timezone_id='America/Los_Angeles', ignore_https_errors=True)
        light_page = day.new_page()
        light_page.clock.install(time=datetime(2026, 10, 15, 17, tzinfo=timezone.utc))
        light_page.goto(args.url + 'app.html?view=about.html')
        light_page.frame_locator('#atlas-view').locator('h1').wait_for()
        assert light_page.locator('html').get_attribute('data-theme') == 'day'
        light_page.screenshot(path=str(screenshots / 'desktop-day.png'))
        assert not errors, errors
        browser.close()
    print('PASS: navigation, fullscreen continuity, history, deep links, data rows, map rendering, manifest, service worker, cached offline page, mobile menu, install control.')


if __name__ == '__main__':
    main()
