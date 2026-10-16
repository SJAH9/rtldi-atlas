(() => {
  if (window.self !== window.top) {
    document.documentElement.classList.add('atlas-embedded');
    return;
  }
  if (!/^https?:$/.test(location.protocol)) return;
  const current = new URL(location.href);
  if (current.searchParams.get('plain') === '1') return;
  const view = current.pathname.split('/').pop() + current.search + current.hash;
  const app = new URL('app.html', current);
  app.searchParams.set('view', view);
  location.replace(app.href);
})();
