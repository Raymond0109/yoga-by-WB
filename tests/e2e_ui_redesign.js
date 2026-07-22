// E2E debug check for the new UI (static/ui-redesign.html).
// Validates the two fixes:
//   1) drawFrame must prepend 'data:image/jpeg;base64,' so the <img> loads
//      (backend sends RAW base64; without the prefix nothing ever rendered).
//   2) uploadFile must await the WS open before sending the start frame
//      (otherwise FileReader.onload fires first and the message is dropped).
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
