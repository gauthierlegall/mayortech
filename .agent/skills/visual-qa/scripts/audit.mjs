#!/usr/bin/env node
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const targetUrl = process.argv[2] || 'http://127.0.0.1:19860/demo.html';
const outDir = path.resolve(__dirname, '../../../.agent/tmp/qa');
fs.mkdirSync(outDir, { recursive: true });

const desktopImg = path.join(outDir, 'desktop.png');
const mobileImg = path.join(outDir, 'mobile.png');

console.log(`[Visual-QA] Démarrage de l'audit sur : ${targetUrl}`);

async function runAudit() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true }).catch(async () => {
    return await chromium.launch({ headless: true });
  });

  const errors = [];

  // ==========================================
  // 1. Audit Desktop 1920x1080
  // ==========================================
  const contextDesktop = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
  });
  const pageDesktop = await contextDesktop.newPage();

  pageDesktop.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`[Console Error - Desktop] ${msg.text()}`);
    }
  });

  pageDesktop.on('pageerror', (err) => {
    errors.push(`[Page Error - Desktop] ${err.message}`);
  });

  await pageDesktop.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await pageDesktop.waitForTimeout(1000);

  // Auto-connect if on profile screen
  const radio = pageDesktop.locator('input[name="work-profile"]').first();
  if (await radio.count() > 0) {
    await radio.check();
    const openBtn = pageDesktop.locator('button:has-text("Ouvrir mon espace")').first();
    if (await openBtn.count() > 0) {
      await openBtn.click();
      await pageDesktop.waitForTimeout(800);
    }
  }

  // Go to workflows if needed
  if (!pageDesktop.url().includes('#/workflows')) {
    await pageDesktop.goto(`${targetUrl}#/workflows`, { waitUntil: 'networkidle' });
    await pageDesktop.waitForTimeout(1000);
  }

  // Assertion: Check horizontal overflow
  const desktopOverflow = await pageDesktop.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth;
  });
  if (desktopOverflow) {
    errors.push('Débordement horizontal détecté sur Desktop (scrollWidth > innerWidth).');
  }

  // Assertion: Text contrast / invisible headings
  const invisibleHeading = await pageDesktop.evaluate(() => {
    const headings = Array.from(document.querySelectorAll('h1, h2, h3'));
    for (const h of headings) {
      const style = window.getComputedStyle(h);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      if (parseFloat(style.opacity) === 0) return `Titre invisible (opacity=0) : ${h.textContent}`;
      const color = style.color;
      // Get background color of parent
      let el = h.parentElement;
      while (el && el !== document.body) {
        const bg = window.getComputedStyle(el).backgroundColor;
        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
          if (color === bg) {
            return `Titre avec texte identique au fond (${color}) : ${h.textContent}`;
          }
          break;
        }
        el = el.parentElement;
      }
    }
    return null;
  });
  if (invisibleHeading) {
    errors.push(invisibleHeading);
  }

  // Assertion: Check text/background contrast on #102A4C buttons
  const buttonContrastErrors = await pageDesktop.evaluate(() => {
    const navyBtns = Array.from(document.querySelectorAll('button, a')).filter((el) => {
      const bg = window.getComputedStyle(el).backgroundColor;
      return bg === 'rgb(16, 42, 76)' || bg.includes('16, 42, 76');
    });
    const errs = [];
    for (const b of navyBtns) {
      const textColor = window.getComputedStyle(b).color;
      const span = b.querySelector('span');
      const spanColor = span ? window.getComputedStyle(span).color : textColor;
      if (textColor.includes('0, 0, 0') || spanColor.includes('0, 0, 0')) {
        errs.push(`Bouton bleu marine #102A4C avec texte sombre/noir non conforme : "${b.textContent.trim()}"`);
      }
    }
    return errs;
  });
  if (buttonContrastErrors.length > 0) {
    errors.push(...buttonContrastErrors);
  }

  // Assertion: React Flow canvas height >= 450px
  const canvasHeight = await pageDesktop.evaluate(() => {
    const rf = document.querySelector('.react-flow') || document.querySelector('[class*="PixelFlowCanvas"]') || document.querySelector('.react-flow__renderer');
    return rf ? rf.getBoundingClientRect().height : null;
  });
  if (canvasHeight !== null && canvasHeight < 450) {
    errors.push(`Hauteur du canvas React Flow insuffisante : ${canvasHeight}px < 450px`);
  }

  // ==========================================
  // RGAA 4.1 / WCAG 2.1 AA Audit (axe-core)
  // ==========================================
  console.log(`[Visual-QA] Analyse RGAA 4.1 / WCAG 2.1 AA via @axe-core/playwright...`);
  try {
    const axeResults = await new AxeBuilder({ page: pageDesktop })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    const criticalOrSerious = axeResults.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );

    if (criticalOrSerious.length > 0) {
      console.warn(`[Visual-QA Accessibilité] ${criticalOrSerious.length} violations critiques/sérieuses détectées :`);
      for (const v of criticalOrSerious) {
        console.warn(` - [${v.impact.toUpperCase()}] ${v.id}: ${v.description} (${v.nodes.length} occurrences)`);
        errors.push(`Accessibilité RGAA [${v.impact.toUpperCase()}] ${v.id}: ${v.description}`);
      }
    } else {
      console.log(`[Visual-QA Accessibilité] 0 violation critique ou sérieuse WCAG 2.1 AA détectée !`);
    }
  } catch (axeErr) {
    console.warn(`[Visual-QA Accessibilité] Scan axe-core avertissement :`, axeErr.message);
  }

  // Capture Desktop
  await pageDesktop.screenshot({ path: desktopImg, fullPage: false });
  console.log(`[Visual-QA] Capture Desktop enregistrée : ${desktopImg}`);
  await contextDesktop.close();

  // ==========================================
  // 2. Audit Mobile 390x844
  // ==========================================
  const contextMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    locale: 'fr-FR',
    isMobile: true,
  });
  const pageMobile = await contextMobile.newPage();

  pageMobile.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`[Console Error - Mobile] ${msg.text()}`);
    }
  });

  await pageMobile.goto(`${targetUrl}#/workflows`, { waitUntil: 'networkidle', timeout: 30000 });
  await pageMobile.waitForTimeout(800);

  // Assertion: Mobile horizontal overflow
  const mobileOverflow = await pageMobile.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth;
  });
  if (mobileOverflow) {
    errors.push('Débordement horizontal détecté sur Mobile (scrollWidth > innerWidth).');
  }

  // Capture Mobile
  await pageMobile.screenshot({ path: mobileImg, fullPage: false });
  console.log(`[Visual-QA] Capture Mobile enregistrée : ${mobileImg}`);
  await contextMobile.close();

  await browser.close();

  if (errors.length > 0) {
    console.error('\n[Visual-QA ÉCHEC] Erreurs bloquantes constatées :');
    for (const err of errors) {
      console.error(` - ❌ ${err}`);
    }
    process.exit(1);
  }

  console.log('\n[Visual-QA SUCCÈS] Toutes les assertions DOM et viewport sont validées avec succès !');
}

runAudit().catch((err) => {
  console.error('[Visual-QA Fatal Error]', err);
  process.exit(1);
});
