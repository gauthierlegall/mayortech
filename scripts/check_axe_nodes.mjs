import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true }).catch(() => chromium.launch({ headless: true }));
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:19875/demo.html', { waitUntil: 'networkidle' });
  const radio = page.locator('input[name="work-profile"]').first();
  if (await radio.count() > 0) {
    await radio.check();
    await page.locator('button:has-text("Ouvrir mon espace")').first().click();
    await page.waitForTimeout(800);
  }
  await page.goto('http://127.0.0.1:19875/demo.html#/workflows', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  for (const v of axe.violations.filter(x => x.impact === 'critical' || x.impact === 'serious')) {
    console.log(`\n=== [${v.impact.toUpperCase()}] ${v.id}: ${v.description} ===`);
    for (const node of v.nodes.slice(0, 5)) {
      console.log('Target:', node.target);
      console.log('HTML:', node.html);
      console.log('Failure summary:', node.failureSummary);
    }
  }
  await browser.close();
}

main().catch(console.error);
