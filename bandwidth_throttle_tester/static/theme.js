// Apply the saved theme before styles load to avoid a bright flash on reload.
(() => {
  const key = 'nrl-theme';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = null;
  try {
    const saved = localStorage.getItem(key);
    if (saved === 'dark' || saved === 'light') preference = saved;
  } catch { /* The toggle still works when browser storage is unavailable. */ }

  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    const dark = theme === 'dark';
    const action = `Switch to ${dark ? 'light' : 'dark'} mode`;
    toggle.setAttribute('aria-pressed', String(dark));
    toggle.setAttribute('aria-label', action);
    toggle.title = action;
    document.getElementById('theme-icon').textContent = dark ? '☀' : '☾';
    document.getElementById('theme-label').textContent = dark ? 'Light mode' : 'Dark mode';
  }

  apply(preference || (system.matches ? 'dark' : 'light'));
  system.addEventListener('change', event => {
    if (!preference) apply(event.matches ? 'dark' : 'light');
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply(document.documentElement.dataset.theme);
    document.getElementById('theme-toggle').addEventListener('click', () => {
      preference = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(key, preference); } catch { /* Session-only fallback. */ }
      apply(preference);
    });
  });
})();
