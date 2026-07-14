const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--allow-file-access-from-files'
    ]
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 960, deviceScaleFactor: 1 });
  const errors = [];
  page.on('console', msg => {
    const txt = msg.text();
    if (txt.includes('error') || txt.includes('Error') || txt.includes('fail')) errors.push(txt);
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0' });

  // Pick a known asana
  await page.select('#asanaSel', 'warrior_2');
  await new Promise(r => setTimeout(r, 500));

  // Upload image
  const input = await page.$('#fileImage');
  await input.uploadFile('/Users/ching-juichang/Yoga_project_v1_workbuddy/data/uploads/01c33c2c86d74f1e91d4a4be661aaa25.jpg');

  // Wait for analysis to arrive and 3D avatar to populate
  let state = null;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1000));
    state = await page.evaluate(() => {
      const s = window.Avatar3D && window.Avatar3D.getMuscleState ? window.Avatar3D.getMuscleState() : null;
      return s ? { n: s.length, visible: s.filter(u => u.visible).length, first: s[0] } : null;
    });
    console.log('attempt', i + 1, JSON.stringify(state));
    if (state && state.visible > 10) break;
  }

  if (!state || state.visible < 10) {
    console.error('FAIL: 3D muscles not visible', state);
    await browser.close();
    process.exit(1);
  }

  // Rotate the 3D view so the half-lens shape is visible from an oblique angle.
  const canvas3d = await page.$('#view3d');
  const box = await canvas3d.boundingBox();
  await page.mouse.move(box.x + box.width/2, box.y + box.height/2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width/2 - 200, box.y + box.height/2 - 80, { steps: 20 });
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 500));

  await canvas3d.screenshot({ path: '/tmp/avatar3d_fusiform.png' });

  // Check shape: half-lens scale should have radius roughly equal on x/z and length on y.
  const shapeCheck = await page.evaluate(() => {
    const s = window.Avatar3D.getMuscleState();
    let minRatio = Infinity, maxRatio = 0;
    for (const u of s) {
      if (!u.visible) continue;
      const [rx, ly, rz] = u.scale;
      const ratio = Math.max(rx, rz) / ly;
      minRatio = Math.min(minRatio, ratio);
      maxRatio = Math.max(maxRatio, ratio);
    }
    return { minRatio, maxRatio, count: s.length };
  });
  console.log('shape ratios:', shapeCheck);

  // Require that muscles are thin enough to avoid blob-like appearance.
  if (shapeCheck.maxRatio > 0.45) {
    console.error('FAIL: muscles look too thick; max ratio', shapeCheck.maxRatio);
    await browser.close();
    process.exit(1);
  }

  // Color must vary across muscles (stretch is per-muscle, not uniform).
  const colors = await page.evaluate(() => window.Avatar3D.getMuscleState()
    .map(u => [Math.round(u.color[0]*4), Math.round(u.color[1]*4), Math.round(u.color[2]*4)]));
  const distinct = new Set(colors.map(c => c.join(','))).size;
  console.log('distinct muscle color buckets:', distinct);
  if (distinct < 2) {
    console.error('FAIL: all muscles share one color (stretch not driving hue)');
    await browser.close();
    process.exit(1);
  }

  if (errors.length) console.warn('console errors:', errors);
  console.log('PASS: 3D avatar muscles updated to half-lens model');
  await browser.close();
})();
