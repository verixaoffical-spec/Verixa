/* T-036: the Risk Analysis charts and history, on the real app with the seeded demo data (scripts/seed_demo.py).
 * Latest result per PR: #1 High, #2 Medium, #3 Low, #4 High (needs review), #5 failed, #6 High (hostile text).
 * PR #7 (High) also has an older commit, scored Medium two days ago.
 */
import { expect, test } from '@playwright/test';
import { closePages, openRisk, rowOf, signIn } from './helpers';

test.afterEach(closePages);

test('charts show the real counts, with details, a table view and the risk history', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page);

  const charts = page.getByLabel('Risk charts');
  await expect(charts).toBeVisible();
  await expect(charts.getByRole('img', { name: /^Risk distribution: 4 High, 1 Medium, 1 Low/ })).toBeVisible();
  await expect(charts.getByRole('img', { name: /^Analysis status: 5 Scored, 1 Needs review, 0 Running, 1 Failed/ })).toBeVisible();

  // today: #1..#7 newest rows; two days ago: the older commit of #7
  const bars = charts.locator('.rbar');
  await expect(bars).toHaveCount(7);
  await expect(bars.nth(6)).toHaveAttribute('aria-label', /: 4 High, 1 Medium, 1 Low, 1 not scored$/);
  await expect(bars.nth(4)).toHaveAttribute('aria-label', /: 0 High, 1 Medium, 0 Low, 0 not scored$/);
  await bars.nth(6).hover();
  await expect(charts.getByRole('tooltip')).toContainText('High');

  await charts.getByRole('button', { name: 'View as table' }).click();
  await expect(charts.locator('table tbody tr')).toHaveCount(7);
  await charts.getByRole('button', { name: 'View as chart' }).click();

  await expect(charts.locator('.rissue', { hasText: 'Sensitive area' })).toHaveAttribute('title', 'Sensitive area: 2 High, 0 Medium, 0 Low');

  // history: PR #7 moved from Medium to High
  await rowOf(page, 7).first().click();
  const history = page.locator('.rhist li');
  await expect(history).toHaveCount(2);
  await expect(history.nth(0)).toContainText('High');
  await expect(history.nth(1)).toContainText('Medium');

  // the hostile title is shown as text and never runs
  expect(problems).toEqual([]);
});

test('an account with no analysed pull requests sees no charts, only the empty state', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'other@verixa.dev', baseURL!);
  await openRisk(page);
  await expect(page.getByRole('tabpanel', { name: 'Overview' }).getByText('No pull requests analysed yet')).toBeVisible();
  await expect(page.getByLabel('Risk charts')).toHaveCount(0);
  expect(problems).toEqual([]);
});
