// Shared helpers for real-data E2E runs.
// All steps share a single browser/context per spec (one login per step file).
const fs = require('fs');
const path = require('path');

const FRONTEND = process.env.FRONTEND || 'http://localhost:4201';
const API = process.env.API || 'http://localhost:8011';
const SCREENSHOT_DIR = path.resolve(__dirname, '../../docs/qa/screenshots/real-data-r1');

function ensureScreenshotDir() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function shotPath(name) {
  ensureScreenshotDir();
  return path.join(SCREENSHOT_DIR, `${name}.png`);
}

function evidencePath(name) {
  ensureScreenshotDir();
  return path.join(SCREENSHOT_DIR, name);
}

function writeEvidence(name, content) {
  fs.writeFileSync(evidencePath(name), content);
}

module.exports = { FRONTEND, API, SCREENSHOT_DIR, shotPath, evidencePath, writeEvidence };
