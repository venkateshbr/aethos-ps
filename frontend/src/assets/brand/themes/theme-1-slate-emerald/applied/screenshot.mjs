// Headless screenshot script for issue #89 — captures the founder-picked
// theme-1-slate-emerald applied to the live landing + shell templates plus
// the four hero surfaces from the original mockup. Reads the same Tailwind
// tokens we wired into frontend/tailwind.config.js, so what you see here is
// what the live app would render once the unrelated build-blockers are fixed.
//
// Run:
//   node frontend/src/assets/brand/themes/theme-1-slate-emerald/applied/screenshot.mjs
//
// Outputs PNGs into the same directory.
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const APPLIED_DIR = path.dirname(new URL(import.meta.url).pathname);
const THEME_DIR   = path.dirname(APPLIED_DIR);

const shots = [
  {
    name:   '01-landing',
    file:   path.join(APPLIED_DIR, 'landing-rendered.html'),
    full:   true,
    width:  1440,
    height: 900,
  },
  {
    name:   '02-shell-copilot',
    file:   path.join(APPLIED_DIR, 'shell-rendered.html'),
    full:   false,
    width:  1440,
    height: 900,
  },
  {
    name:   '03-mockup-inbox',
    file:   path.join(THEME_DIR, 'mockup.html'),
    // Clip to the HITL inbox section (sections are ~520px tall starting at ~660)
    full:   false,
    width:  1280,
    height: 1700,
  },
  {
    name:   '04-mockup-invoice-list',
    file:   path.join(THEME_DIR, 'mockup.html'),
    full:   false,
    width:  1280,
    height: 2400,
  },
  {
    name:   '05-mockup-signup-hero',
    file:   path.join(THEME_DIR, 'mockup.html'),
    full:   true,
    width:  1280,
    height: 900,
  },
];

const browser = await chromium.launch();
try {
  for (const shot of shots) {
    const ctx = await browser.newContext({
      viewport: { width: shot.width, height: shot.height },
      deviceScaleFactor: 2,
    });
    const page = await ctx.newPage();
    await page.goto(pathToFileURL(shot.file).toString(), { waitUntil: 'networkidle' });
    // Tailwind CDN injects styles asynchronously; give it a beat.
    await page.waitForTimeout(800);
    const outPath = path.join(APPLIED_DIR, `${shot.name}.png`);
    await page.screenshot({ path: outPath, fullPage: shot.full });
    console.log(`wrote ${path.relative(process.cwd(), outPath)}`);
    await ctx.close();
  }
} finally {
  await browser.close();
}
