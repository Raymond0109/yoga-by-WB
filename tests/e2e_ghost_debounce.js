// Verifies the ghost-switch debounce: in auto-detect mode the detected asana
// id flickers frame-to-frame. The ghost must NOT reload on a single-frame
// flicker, only once a candidate is stable for GHOST_STABLE_FRAMES frames.
// Regression test for the "ghost wobbles / not the same coordinate system" bug.
const puppeteer = require('puppeteer');

(async () => {
  const base = process.env.BASE_URL || 'http://127.0.0.1:8000/';
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));

  await page.goto(base, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForFunction('typeof window.Avatar3D !== "undefined" && typeof maybeLoadGhost === "function"', { timeout: 15000 });

  const result = await page.evaluate(async () => {
    // Spy on setGhost to count actual ghost reloads.
    let reloads = 0;
    const orig = window.Avatar3D.setGhost.bind(window.Avatar3D);
    window.Avatar3D.setGhost = (w) => { reloads++; return orig(w); };

    // 1) Flicker: single-frame changes must NOT reload.
    maybeLoadGhost('warrior2');
    maybeLoadGhost('tree');
    maybeLoadGhost('warrior2');
    maybeLoadGhost('tree');
    const afterFlicker = reloads;

    // 2) Stable candidate: 5 consecutive same ids must reload exactly once.
    for (let i = 0; i < 5; i++) maybeLoadGhost('tree');
    // allow the async fetch in loadGhost() to resolve
    await new Promise(r => setTimeout(r, 600));
    const afterStable = reloads;

    return { afterFlicker, afterStable };
  });

  await browser.close();

  let ok = true;
  if (result.afterFlicker !== 0) {
    console.error('FAIL: flicker caused', result.afterFlicker, 'ghost reload(s)');
    ok = false;
  }
  if (result.afterStable !== 1) {
    console.error('FAIL: stable candidate reloaded', result.afterStable, 'time(s), expected 1');
    ok = false;
  }
  if (errors.length) { console.error('FAIL: console errors:', errors); ok = false; }

  if (ok) { console.log('PASS: ghost debounce —', JSON.stringify(result), 'no console errors'); process.exit(0); }
  else process.exit(1);
})();
