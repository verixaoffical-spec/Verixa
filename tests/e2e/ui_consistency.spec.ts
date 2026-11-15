/* T-097 on the real app: the dashboard uses the landing page's wording and its card surface (shared/cards.css), every
 * Risk card has the same depth, and Analyses per day is its own full-width section whose View as table expands it
 * into the full table and back, smoothly unless the viewer asked for less motion.
 */
import { expect, test, type Page } from '@playwright/test';
import { closePages, openRisk, signIn } from './helpers';

test.afterEach(closePages);

const perDay = (page: Page) => page.getByRole('region', { name: 'Analyses per day' });
const style = (page: Page, sel: string, prop: string) =>
  page.locator(sel).first().evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);

test('the dashboard speaks the landing page\'s words and wears its card surface, with one depth everywhere', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);

  // the landing page's own terms (frontend/src/landing/MockDashboard.tsx)
  await page.goto('/');
  await expect(page.locator('.mock-title')).toHaveText('Pull Requests');
  await expect(page.locator('.mock-table thead th')).toHaveText(['Pull request', 'Risk', 'Tests', 'Status']);
  await expect(page.locator('.mock-feed-head')).toContainText('Agent activity');
  const landingFill = await style(page, '.mock-card', 'background-image');

  await openRisk(page, 'Pull Requests');
  await expect(page.locator('.rnav').getByRole('tab').first()).toHaveText('Pull Requests');
  await expect(page.getByRole('tabpanel', { name: 'Pull Requests' }).getByRole('heading', { name: 'Pull Requests' })).toBeVisible();
  await expect(page.getByRole('tabpanel', { name: 'Pull Requests' }).locator('thead th')).toHaveText(['Pull request', 'Author', 'Risk', 'Status', 'Updated']);

  await page.getByRole('tab', { name: 'Overview', exact: true }).click();
  const overview = page.getByRole('tabpanel', { name: 'Overview' });
  await expect(overview.locator('section.rtable thead th')).toHaveText(['Pull request', 'Risk', 'Score', 'Status', 'Analysed']);

  // one surface: the dashboard cards are filled exactly like the landing page's cards, and all share one shadow
  await expect.poll(() => style(page, '[aria-label="Overview"] .rchart', 'background-image')).toBe(landingFill);
  const shadows = new Set<string>();
  for (const sel of ['[aria-label="Overview"] .rchart', '[aria-label="Overview"] section.rtable', '[aria-label="Overview"] .risk-stat']) {
    const shadow = await style(page, sel, 'box-shadow');
    expect(shadow, `${sel} has depth`).toMatch(/rgba?\(.+\) 0px \d+px \d+px -\d+px/);
    shadows.add(shadow);
  }
  expect(shadows.size).toBe(1);

  // the same in the light theme: the landing page and the dashboard still share one fill and one shadow
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  const lightCard = [await style(page, '[aria-label="Overview"] .rchart', 'background-color'), await style(page, '[aria-label="Overview"] .rchart', 'box-shadow')];
  await page.goto('/');
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  expect([await style(page, '.mock-card', 'background-color'), await style(page, '.mock-card', 'box-shadow')]).toEqual(lightCard);
  expect(problems).toEqual([]);
});

test('Analyses per day is its own full-width section, and View as table expands it into the full table and back', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openRisk(page, 'Overview');
  const day = perDay(page);
  await expect(day).toBeVisible();

  // separate: not inside the row of small charts, below it, and as wide as that row
  await expect(page.locator('.rcharts [aria-label="Analyses per day"]')).toHaveCount(0);
  const row = (await page.locator('[aria-label="Overview"] .rcharts').boundingBox())!;
  const box = (await day.boundingBox())!;
  expect(box.y).toBeGreaterThan(row.y + row.height - 1);
  expect(Math.abs(box.width - row.width)).toBeLessThan(2);
  await expect(day.locator('.rbar')).toHaveCount(7);

  // the table: every day, a total per day and for the week, with room for every column
  const bars = await day.locator('.rbar').evaluateAll(els => els.map(e => e.getAttribute('aria-label')!));
  const week = bars.map(l => (l.match(/\d+(?= (High|Medium|Low|not scored))/g) ?? []).map(Number).reduce((a, b) => a + b, 0));
  await day.getByRole('button', { name: 'View as table' }).click();
  await expect(day.getByRole('button', { name: 'View as chart' })).toHaveAttribute('aria-expanded', 'true');
  const table = day.locator('table');
  await expect(table.locator('thead th')).toHaveText(['Day', 'High', 'Medium', 'Low', 'Not scored', 'Total']);
  await expect(table.locator('tbody tr')).toHaveCount(7);
  await expect(table.locator('tbody tr td:last-child')).toHaveText(week.map(String));
  await expect(table.locator('tfoot td').last()).toHaveText(String(week.reduce((a, b) => a + b, 0)));
  await expect.poll(async () => (await table.boundingBox())!.width).toBeGreaterThan(box.width * 0.9);
  const wrap = await day.locator('.tablewrap').evaluate(el => [el.scrollWidth, el.clientWidth]);
  expect(wrap[0]).toBeLessThanOrEqual(wrap[1]);  // no clipped columns, no sideways scroll
  await expect.poll(async () => Math.round((await day.locator('.rbars').boundingBox())!.height)).toBe(150);  // the chart steps back

  // the open animation really runs; View as chart takes the table away again
  expect(await style(page, '.rday-more', 'animation-name')).toBe('rday-open');
  await day.getByRole('button', { name: 'View as chart' }).click();
  await expect(day.getByRole('button', { name: 'View as table' })).toHaveAttribute('aria-expanded', 'false');
  await expect(day.locator('table')).toHaveCount(0);
  await expect.poll(async () => Math.round((await day.locator('.rbars').boundingBox())!.height)).toBe(240);
  expect(problems).toEqual([]);
});

test('with reduced motion the table opens and closes at once, with no animation', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await openRisk(page, 'Overview');
  await perDay(page).getByRole('button', { name: 'View as table' }).click();
  expect(await style(page, '.rday-more', 'animation-name')).toBe('none');
  await perDay(page).getByRole('button', { name: 'View as chart' }).click();
  await expect(perDay(page).locator('table')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('negative: an account with nothing analysed gets no Analyses per day section and no charts', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'other@verixa.dev', baseURL!);
  await openRisk(page, 'Overview');
  await expect(page.getByRole('tabpanel', { name: 'Overview' }).getByText('No pull requests analysed yet')).toBeVisible();
  await expect(perDay(page)).toHaveCount(0);
  await expect(page.getByLabel('Risk charts')).toHaveCount(0);
  expect(problems).toEqual([]);
});
