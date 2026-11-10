// Pull the live brand (resolved from the newest brand skill in Claude's
// settings on every request) and paint it onto CSS variables. Shared by both
// the dashboard and the profile screen so a brand-skill change shows up
// everywhere on next load — nothing is hard-coded.
async function applyBrand() {
  let brand;
  try {
    brand = await (await fetch('/api/branding')).json();
  } catch (e) {
    return; // CSS defaults already cover this
  }
  const root = document.documentElement.style;
  const c = brand.colors || {};
  Object.entries(c).forEach(([k, v]) => root.setProperty('--' + k, v));
  // Fonts shipped inside the brand skill (e.g. Open Sans) — load them so the
  // typeface renders even where it isn't installed.
  if ((brand.font_faces || []).length) {
    const css = brand.font_faces.map(ff => `@font-face{font-family:'${ff.family}';` +
      `src:url('${ff.url}');font-weight:${ff.weight};font-style:${ff.style};font-display:swap}`).join('');
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  }
  const f = brand.fonts || {};
  if (f.heading) root.setProperty('--font-heading', f.heading);
  if (f.body) root.setProperty('--font-body', f.body);

  // Brand name + logo in the top bar, when present.
  document.querySelectorAll('[data-brand-name]').forEach(el => {
    el.textContent = (brand.name || 'NTXP');
  });
  if (brand.logo_url) {
    document.querySelectorAll('[data-brand-logo]').forEach(img => {
      img.src = brand.logo_url; img.style.display = 'block';
      img.onerror = () => { img.style.display = 'none'; };
    });
    // The logo carries the name — don't repeat it beside the logo.
    document.querySelectorAll('.topbar [data-brand-name]').forEach(el => el.style.display = 'none');
  }
  window.__brand = brand;
}
applyBrand();
