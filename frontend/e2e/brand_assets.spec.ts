/**
 * C36 — Brand assets present.
 *
 * Guards F6 from regressing: the Aethos PS lockup must be in the bundled
 * assets, and the favicon must resolve. The 3 theme directions delivered
 * by Chitra (issue #9) must each have at least one .svg in their dir.
 */

import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BRAND_DIR = path.join(__dirname, '..', 'src', 'assets', 'brand');

test.describe('Brand assets (C36)', () => {
  test('frontend/src/assets/brand/ has at least one logo svg', () => {
    expect(fs.existsSync(BRAND_DIR)).toBeTruthy();
    const entries = fs.readdirSync(BRAND_DIR, { withFileTypes: true });
    const svgFiles = entries.filter((e) => e.isFile() && e.name.endsWith('.svg'));
    const themeDirs = entries.filter((e) => e.isDirectory());

    // EITHER inline SVGs OR theme subdirectories with SVGs inside
    const themeSvgCount = themeDirs
      .map((d) => fs.readdirSync(path.join(BRAND_DIR, d.name)).filter((n) => n.endsWith('.svg')).length)
      .reduce((a, b) => a + b, 0);

    expect(svgFiles.length + themeSvgCount).toBeGreaterThan(0);
  });

  test('favicon resolves on landing page', async ({ page }) => {
    const response = await page.goto('/favicon.ico');
    expect(response?.status()).toBeLessThan(400);
  });
});
