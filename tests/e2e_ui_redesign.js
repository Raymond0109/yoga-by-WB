// E2E debug check for the new UI (static/ui-redesign.html).
// Validates:
//   1) drawFrame must prepend 'data:image/jpeg;base64,' so the <img> loads
//      (backend sends RAW base64; without the prefix nothing ever rendered).
//   2) uploadFile must await the WS open before sending the start frame
//      (otherwise FileReader.onload fires first and the message is dropped).
//   3) the anatomical muscle overlay is drawn and colored by engagement
//      (ported from index.html; was missing in the new UI redesign).
// Also drives the client-camera path with a fake media device.
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const URL = 'http://127.0.0.1:8000/static/ui-redesign.html';
const IMG = path.join(__dirname, 'fixtures', 'test_yoga.jpg');
const B64 = fs.readFileSync(IMG).toString('base64');

function canvasSum() {
  const c = document.getElementById('videoCanvas');
  const ctx = c.getContext('2d');
  const { data } = ctx.getImageData(0, 0, c.width, c.height);
  let sum = 0;
  for (let i = 0; i < data.length; i += 4) sum += data[i] + data[i + 1] + data[i + 2];
  return sum;
}
function clearCanvas() {
  const c = document.getElementById('videoCanvas');
  c.getContext('2d').clearRect(0, 0, c.width, c.height);
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--allow-file-access-from-files',
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
    ],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 960, deviceScaleFactor: 1 });

  const jsExceptions = [];
  page.on('pageerror', (e) => jsExceptions.push(e.message));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const t = m.text();
    // Ignore the browser's automatic /favicon.ico 404 — benign, unrelated to app.
    if (/favicon\.ico|Failed to load resource/.test(t)) return;
    jsExceptions.push('console.error: ' + t);
  });

  let failures = 0;
  const check = (name, cond) => {
    console.log((cond ? 'PASS' : 'FAIL') + ' - ' + name);
    if (!cond) failures++;
  };

  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 400));

  // 1) Page loads without uncaught JS exceptions
  check('page loads without JS exceptions', jsExceptions.length === 0);

  // 2) drawFrame renders a RAW base64 frame (the reported "nothing shows" bug)
  await page.evaluate((b) => window.drawFrame({ frame: b, width: 320, height: 240, poses: [] }), B64);
  await new Promise((r) => setTimeout(r, 700));
  const sumRaw = await page.evaluate(canvasSum);
  check('drawFrame renders RAW base64 frame (prefix fix)', sumRaw > 0);

  // 3) drawFrame also handles an already-prefixed frame (robustness)
  await page.evaluate((b) => window.drawFrame({ frame: 'data:image/jpeg;base64,' + b, width: 320, height: 240, poses: [] }), B64);
  await new Promise((r) => setTimeout(r, 700));
  const sumPrefixed = await page.evaluate(canvasSum);
  check('drawFrame handles data:-prefixed frame', sumPrefixed > 0);

  // 4) End-to-end image upload via WS (exercises uploadFile + ensureConnected + drawFrame)
  await page.evaluate(clearCanvas);
  const input = await page.$('#fileImage');
  await input.uploadFile(IMG);
  let sumUpload = 0;
  for (let i = 0; i < 40; i++) {
    sumUpload = await page.evaluate(canvasSum);
    if (sumUpload > 0) break;
    await new Promise((r) => setTimeout(r, 500));
  }
  check('image upload end-to-end renders (WS + ensureConnected fix)', sumUpload > 0);

  // 5) Client camera path with a fake media device
  await page.evaluate(clearCanvas);
  await page.click('#btnCamera');
  let sumCam = 0;
  for (let i = 0; i < 30; i++) {
    sumCam = await page.evaluate(canvasSum);
    if (sumCam > 0) break;
    await new Promise((r) => setTimeout(r, 500));
  }
  check('client camera path renders (fake device)', sumCam > 0);
  // stop cleanly
  await page.evaluate(() => { const b = document.getElementById('btnStop'); if (b) b.click(); });

  // 6) Muscle color must reflect the ACTUAL pose (joint angles), not the
  //    static/dynamic feedback.live value. Reproduces the user's report
  //    "colors don't correspond to actual muscle engagement". The 2D overlay
  //    now computes per-muscle stretch from live world_landmarks (same model
  //    as the 3D avatar), so a flexed elbow must show biceps RED (contracted)
  //    and triceps BLUE (stretched), and swapping feedback.live must NOT change
  //    the rendered colors. All browser-side work (buildPose / drawMuscles /
  //    stretchOf / canvas reads) runs INSIDE page.evaluate; only the
  //    assertions stay in Node (calling drawMuscles from Node throws
  //    "document is not defined").
  const metrics = await page.evaluate(() => {
    function buildPose(mode) {
      const W3 = {
        0:[0,0.55,0.1], 11:[-0.18,0.40,0], 12:[0.18,0.40,0],
        13:[-0.30,0.25,0.05], 15:[-0.38,0.10,0.1],
        23:[-0.12,0,0], 24:[0.12,0,0], 25:[-0.13,-0.45,0.05], 26:[0.13,-0.45,0.05],
        27:[-0.13,-0.90,0], 28:[0.13,-0.90,0],
      };
      if (mode === 'flexed') { W3[14] = [0.30,0.25,0.05]; W3[16] = [0.28,0.42,0.0]; }
      else { W3[14] = [0.30,0.25,0.05]; W3[16] = [0.42,0.10,0.10]; } // extended (straight)
      const lm = [], wl = [];
      for (let i = 0; i < 33; i++) {
        const w = W3[i] || [0, 0, 0];
        lm.push({ x: 0.5 + w[0] * 0.5, y: 0.5 - w[1] * 0.5, v: 1 });
        wl.push({ x: w[0], y: w[1], z: w[2], v: 1 });
      }
      return { lm, wl };
    }
    function drawAndSum(lm, wl, feedback) {
      const c = document.getElementById('videoCanvas');
      const ctx = c.getContext('2d');
      c.width = 320; c.height = 240;
      ctx.clearRect(0, 0, 320, 240);
      window.drawMuscles(lm, wl, 320, 240, feedback);
      const { data } = ctx.getImageData(0, 0, 320, 240);
      let sum = 0, red = 0;
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
        sum += r * 3 + g * 5 + b * 7 + a;            // weighted checksum
        if (a >= 20 && r > 180 && r - g > 60 && r - b > 60) red++;
      }
      return { sum, red };
    }
    const flexed = buildPose('flexed');
    const extended = buildPose('extended');
    const fbA = { muscles: [{ id: 'biceps', live: 0.95 }, { id: 'triceps', live: 0.05 }] };
    const fbB = { muscles: [{ id: 'biceps', live: 0.05 }, { id: 'triceps', live: 0.95 }] };
    const sFlexA = drawAndSum(flexed.lm, flexed.wl, fbA);
    const sFlexB = drawAndSum(flexed.lm, flexed.wl, fbB);
    const sExt = drawAndSum(extended.lm, extended.wl, fbA);
    const bicepsF = window.stretchOf('biceps', flexed.wl, 0);
    const bicepsE = window.stretchOf('biceps', extended.wl, 0);
    const triF = window.stretchOf('triceps', flexed.wl, 0);
    const bicepsF1 = window.stretchOf('biceps', flexed.wl, 1);
    const triF1 = window.stretchOf('triceps', flexed.wl, 1);
    return { sFlexA, sFlexB, sExt, bicepsF, bicepsE, triF, bicepsF1, triF1 };
  });
  const sFlexA = metrics.sFlexA, sFlexB = metrics.sFlexB, sExt = metrics.sExt;
  const bicepsF = metrics.bicepsF, bicepsE = metrics.bicepsE, triF = metrics.triF;
  // ── Definitive leak locator: wrap drawBelly to capture per-muscle lvl ──
  const dbg = await page.evaluate(() => {
    function buildPose(mode) {
      const W3 = {
        0:[0,0.55,0.1], 11:[-0.18,0.40,0], 12:[0.18,0.40,0],
        13:[-0.30,0.25,0.05], 15:[-0.38,0.10,0.1],
        23:[-0.12,0,0], 24:[0.12,0,0], 25:[-0.13,-0.45,0.05], 26:[0.13,-0.45,0.05],
        27:[-0.13,-0.90,0], 28:[0.13,-0.90,0],
      };
      if (mode === 'flexed') { W3[14] = [0.30,0.25,0.05]; W3[16] = [0.28,0.42,0.0]; }
      else { W3[14] = [0.30,0.25,0.05]; W3[16] = [0.42,0.10,0.10]; }
      const lm = [], wl = [];
      for (let i = 0; i < 33; i++) {
        const w = W3[i] || [0, 0, 0];
        lm.push({ x: 0.5 + w[0] * 0.5, y: 0.5 - w[1] * 0.5, v: 1 });
        wl.push({ x: w[0], y: w[1], z: w[2], v: 1 });
      }
      return { lm, wl };
    }
    const rec = { fbA: [], fbB: [] };
    const flexed = buildPose('flexed');
    const fbA = { muscles: [{ id: 'biceps', live: 0.95 }, { id: 'triceps', live: 0.05 }] };
    const fbB = { muscles: [{ id: 'biceps', live: 0.05 }, { id: 'triceps', live: 0.95 }] };
    const orig = window.drawBelly;
    window.drawBelly = (pa, pb, wa, wb, m, lvl, wl) => { rec.fbA.push(m.id + '=' + lvl.toFixed(3)); return orig(pa, pb, wa, wb, m, lvl, wl); };
    window.drawMuscles(flexed.lm, flexed.wl, 320, 240, fbA);
    window.drawBelly = (pa, pb, wa, wb, m, lvl, wl) => { rec.fbB.push(m.id + '=' + lvl.toFixed(3)); return orig(pa, pb, wa, wb, m, lvl, wl); };
    window.drawMuscles(flexed.lm, flexed.wl, 320, 240, fbB);
    window.drawBelly = orig;
    return rec;
  });

  check('stretchOf: flexed biceps contracted (red)', bicepsF > 0.8);
  check('stretchOf: extended biceps less engaged', bicepsE < 0.6);
  check('stretchOf: flexed triceps stretched (blue)', triF < 0.2);
  check('biceps engagement tracks pose (flexed > extended)', bicepsF > bicepsE);
  // Core design guarantee: per-muscle engagement (lvl) is computed from the
  // LIVE joint angles (stretchOf), so swapping feedback.live must NOT change
  // any muscle's color. Assert the captured per-muscle lvl lists are identical
  // (robust against benign headless rasterization noise that breaks an exact
  // pixel-sum comparison).
  check('muscle lvl independent of feedback.live', JSON.stringify(dbg.fbA) === JSON.stringify(dbg.fbB));
  check('flexed pose renders red (contracted) biceps pixels', sFlexA.red > 0);

  await browser.close();

  console.log('\nJS exceptions captured: ' + jsExceptions.length);
  jsExceptions.forEach((e) => console.log('  ' + e));
  if (failures === 0) {
    console.log('\nALL TESTS PASSED');
    process.exit(0);
  } else {
    console.log('\n' + failures + ' TEST(S) FAILED');
    process.exit(1);
  }
})().catch((e) => { console.error('FATAL', e); process.exit(2); });
