/* T-095: the Risk Analysis page layout (prompt.txt). View tabs in a pill bar at the very top of the page, then the
 * title, then the overview as cards: KPIs, Analyse, charts, pull request table. Every number comes from the saved
 * feed (/api/analysis/pull-requests); opening the page or switching views never asks the agent to analyse again.
 */
import { expect, test, type Page } from '@playwright/test';
import { closePages, openRisk, signIn } from './helpers';

test.afterEach(closePages);

const top = async (page: Page, selector: string) => (await page.locator(selector).first().boundingBox())!.y;

test('tabs sit at the top, the overview is cards in order, and the numbers are the saved feed', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  const analyses: string[] = [];
  page.on('request', r => { if (r.method() === 'POST' && r.url().includes('/api/analysis')) analyses.push(r.url()); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await openRisk(page);

  const nav = page.locator('section.workspace.risk > .rnav');
  await expect(nav.getByRole('tab')).toHaveText(['Overview', 'Dependency graph', 'Live runs and logs']);
  await expect(nav.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');

  // order on the page: tabs, title, KPI cards, Analyse card, charts, pull request table
  const ys = [await top(page, '.rnav'), await top(page, '.rpage-head h1'), await top(page, '.risk-stats'),
              await top(page, '[aria-label="Analyse a pull request"]'), await top(page, '[aria-label="Risk charts"]'),
              await top(page, 'section.rtable')];
  expect(ys).toEqual([...ys].sort((a, b) => a - b));
  expect(ys[0]).toBeLessThan(80);

  // every number is the saved feed's
  const feed = await (await page.request.get('/api/analysis/pull-requests')).json();
  const values = await page.locator('.risk-stat-value').allTextContents();
  expect(values).toEqual([feed.counts.total, feed.counts.High, feed.counts.Medium, feed.counts.Low].map(String));
  await expect(page.locator('section.rtable tr.risk-row')).toHaveCount(feed.items.length);

  // the donuts are drawn at size (a global 16px icon rule used to shrink them)
  const donut = (await page.locator('.donut-wrap svg').first().boundingBox())!;
  expect(Math.round(donut.width)).toBe(140);

  // the bar stays at the top while scrolling, and switches the view below it
  await page.mouse.wheel(0, 1500);
  await expect.poll(async () => (await nav.boundingBox())!.y).toBeLessThan(30);
  await nav.getByRole('tab', { name: 'Live runs and logs' }).click();
  await expect(page.getByRole('tabpanel', { name: 'Live runs and logs' })).toBeVisible();
  await expect(page.getByRole('tabpanel', { name: 'Overview' })).toHaveCount(0);
  await nav.getByRole('tab', { name: 'Live runs and logs' }).focus();
  await page.keyboard.press('Home');  // keyboard: Home goes back to the first view
  await expect(nav.getByRole('tab', { name: 'Overview' })).toBeFocused();
  await expect(nav.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.risk-stat-value').first()).toHaveText(String(feed.counts.total));

  // the header and rail are Verixa's own, unchanged: still one main navigation with Risk Analysis selected
  await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible();
  expect(analyses).toEqual([]);  // no analysis POST from opening or switching (the graph tab, not opened here, reads GitHub once per commit: D-013)
  expect(problems).toEqual([]);
});

test('at phone width the page does not scroll sideways', async ({ browser, baseURL }) => {
  const { page } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.setViewportSize({ width: 390, height: 844 });
  await openRisk(page);
  await expect(page.locator('.rnav')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('negative: an account with nothing analysed gets the tabs and an empty table card, no charts or rows', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'other@verixa.dev', baseURL!);
  await openRisk(page);
  await expect(page.locator('.rnav').getByRole('tab')).toHaveCount(3);
  await expect(page.locator('section.rtable')).toContainText('No pull requests analysed yet');
  await expect(page.locator('section.rtable tr.risk-row')).toHaveCount(0);
  await expect(page.getByLabel('Risk charts')).toHaveCount(0);
  await expect(page.locator('.risk-stat-value')).toHaveText(['0', '0', '0', '0']);
  expect(problems).toEqual([]);
});
