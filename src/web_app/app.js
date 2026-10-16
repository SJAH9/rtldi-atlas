(() => {
  const pages = new Map([
    ['index.html', 'Overview'], ['global_interactive.html', 'Map'],
    ['full_data.html', 'Full Data'], ['levers.html', 'Levers'],
    ['regression.html', 'Regression'], ['vdem.html', 'Sources'],
    ['world_bank.html', 'Sources'], ['about.html', 'About'],
  ]);
  const base = new URL('./', location.href);
  const frame = document.querySelector('#atlas-view');
  const navigation = document.querySelector('#atlas-navigation');
  const menu = document.querySelector('#atlas-menu');
  const footerMenu = document.querySelector('#atlas-footer-menu');
  const projectLinks = document.querySelector('#atlas-project-links');
  const sources = document.querySelector('#atlas-sources');
  const sourceLinks = document.querySelector('#atlas-source-links');
  const fullscreen = document.querySelector('#atlas-fullscreen');
  const install = document.querySelector('#atlas-install');
  const message = document.querySelector('#atlas-message');
  let currentView = '';
  let installPrompt = null;
  let messageTimer;

  function safeView(value) {
    try {
      const url = new URL(value || 'index.html', base);
      const filename = url.pathname.slice(base.pathname.length);
      if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname) || !pages.has(filename)) return null;
      return filename + url.search + url.hash;
    } catch { return null; }
  }
  function closeMenu() {
    delete navigation.dataset.open;
    menu.setAttribute('aria-expanded', 'false');
    menu.setAttribute('aria-label', 'Open navigation');
    delete projectLinks.dataset.open;
    footerMenu.setAttribute('aria-expanded', 'false');
    footerMenu.setAttribute('aria-label', 'Open project links');
    sourceLinks.hidden = true;
    sources.setAttribute('aria-expanded', 'false');
  }
  function navigate(value, mode = 'push') {
    const view = safeView(value) || 'index.html';
    const filename = new URL(view, base).pathname.split('/').pop();
    document.querySelectorAll('a[data-view]').forEach(link => {
      if (link.dataset.view === filename) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    sources.dataset.active = String(Boolean(sourceLinks.querySelector('a[aria-current="page"]')));
    frame.title = 'RTLDI Atlas: ' + pages.get(filename);
    document.title = pages.get(filename) + ' | RTLDI Atlas 2026';
    const outer = new URL('app.html', base);
    if (view !== 'index.html') outer.searchParams.set('view', view);
    if (mode === 'replace') history.replaceState({ view }, '', outer);
    else if (mode === 'push' && currentView !== view) history.pushState({ view }, '', outer);
    if (currentView !== view) {
      if (currentView) frame.contentWindow.location.replace(new URL(view, base).href);
      else frame.src = new URL(view, base).href;
      currentView = view;
    }
    closeMenu();
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-view]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(link.dataset.view);
  });
  frame.addEventListener('load', () => {
    try {
      const child = frame.contentDocument;
      child.documentElement.classList.add('atlas-embedded');
      syncFullscreen();
      child.addEventListener('click', event => {
        closeMenu();
        const link = event.target.closest('a[href]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.hasAttribute('download')) return;
        const url = new URL(link.href, frame.contentWindow.location.href);
        const view = safeView(url.href);
        if (view && (!link.target || link.target === '_self')) {
          event.preventDefault();
          navigate(view);
        } else if (!view && (!link.target || link.target === '_self')) {
          link.target = '_blank';
          link.rel = 'noopener';
        }
      });
      child.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
    } catch {
      showMessage('This view could not be opened.');
    }
  });
  window.addEventListener('popstate', () => navigate(new URL(location.href).searchParams.get('view'), 'none'));
  menu.addEventListener('click', () => {
    const open = navigation.dataset.open !== 'true';
    closeMenu();
    navigation.dataset.open = String(open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  });
  footerMenu.addEventListener('click', () => {
    const open = projectLinks.dataset.open !== 'true';
    closeMenu();
    projectLinks.dataset.open = String(open);
    footerMenu.setAttribute('aria-expanded', String(open));
    footerMenu.setAttribute('aria-label', open ? 'Close project links' : 'Open project links');
  });
  sources.addEventListener('click', () => {
    const open = sourceLinks.hidden;
    closeMenu();
    sourceLinks.hidden = !open;
    sources.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('click', event => { if (!event.target.closest('.atlas-header,.atlas-footer')) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });

  function showMessage(text) {
    clearTimeout(messageTimer);
    message.textContent = text;
    message.hidden = false;
    messageTimer = setTimeout(() => { message.hidden = true; }, 5000);
  }
  fullscreen.hidden = !document.fullscreenEnabled;
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { showMessage('Fullscreen is unavailable in this browser.'); }
  });
  function syncFullscreen() {
    const active = Boolean(document.fullscreenElement);
    const label = active ? 'Exit fullscreen' : 'Enter fullscreen';
    fullscreen.title = label;
    fullscreen.setAttribute('aria-label', label);
    fullscreen.setAttribute('aria-pressed', String(active));
    fullscreen.querySelector('img').src = active ? 'assets/minimize.svg' : 'assets/maximize.svg';
    try { frame.contentDocument.documentElement.dataset.atlasFullscreen = String(active); } catch {}
    // Keep the existing iframe and its state through all size changes.
    const app = document.querySelector('.atlas-app');
    const header = document.querySelector('.atlas-header');
    const footer = document.querySelector('.atlas-footer');
    app.classList.remove('atlas-compact');
    const crowded = navigation.scrollWidth > navigation.clientWidth + 1 || header.scrollWidth > header.clientWidth + 1 || footer.scrollWidth > footer.clientWidth + 1;
    const smallFullscreen = active && matchMedia('(pointer:coarse)').matches && innerWidth < 1000 && Math.min(innerWidth, innerHeight) < 600;
    const compact = crowded || smallFullscreen;
    app.classList.toggle('atlas-compact', compact);
    if (!compact) closeMenu();
  }
  document.addEventListener('fullscreenchange', syncFullscreen);
  window.addEventListener('resize', syncFullscreen);
  syncFullscreen();
  const standalone = () => matchMedia('(display-mode: standalone)').matches || matchMedia('(display-mode: fullscreen)').matches || navigator.standalone;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    install.hidden = Boolean(standalone());
  });
  install.addEventListener('click', async () => {
    if (!installPrompt) return;
    try {
      await installPrompt.prompt();
      await installPrompt.userChoice;
    } catch { showMessage('Installation is unavailable right now.'); }
    installPrompt = null;
    install.hidden = true;
  });
  window.addEventListener('appinstalled', () => { installPrompt = null; install.hidden = true; });
  function updateTheme() {
    const hour = new Date().getHours();
    document.documentElement.dataset.theme = hour < 7 || hour >= 19 ? 'night' : 'day';
    document.querySelector('meta[name="theme-color"]').content = getComputedStyle(document.documentElement).getPropertyValue('--atlas-surface').trim();
  }
  updateTheme();
  setInterval(updateTheme, 60000);
  function updateNetwork() { document.querySelector('#atlas-network').hidden = navigator.onLine; }
  updateNetwork();
  window.addEventListener('online', updateNetwork);
  window.addEventListener('offline', updateNetwork);
  navigate(new URL(location.href).searchParams.get('view'), 'replace');
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) {
    navigator.serviceWorker.register('sw.js', { scope: './', updateViaCache: 'none' }).catch(() => {});
  }
})();
