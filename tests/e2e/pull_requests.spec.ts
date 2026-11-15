/* T-096 on the real app (tests/e2e/server.py scripts GitHub's pull request list for demo/shop: #1..#7 are the seeded
 * analyses, #8 was never analysed and has a long title, #9 is merged). Covers the Pull Requests section, the saved
 * author, search and expand, the central processing view fed by real agent steps, the tab cache, and multi-line
 * test text.
 */
import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';
import { closePages, openRisk, rowOf, signIn } from './helpers';

test.afterEach(closePages);

const SECRET = 'e2e-only-webhook-secret-0123456789';
const section = (page: Page) => page.getByRole('tabpanel', { name: 'Pull Requests' });
const prRow = (page: Page, n: number) => section(page).locator('tr.risk-row').filter({ has: page.locator(`.rpr-title b:text-is("#${n}")`) });

function count(page: Page, pattern: RegExp, method = 'GET') {
  const seen: string[] = [];
  page.on('request', r => { if (r.method() === method && pattern.test(r.url())) seen.push(r.url()); });
  return seen;
}

test('every pull request is listed first with its author from GitHub, saved, searchable and expandable', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  const syncs = count(page, /\/api\/analysis\/repo-pulls\/sync/, 'POST');
  await openRisk(page, 'Pull Requests');
  await expect(page.locator('.rnav').getByRole('tab').first()).toHaveText('Pull Requests');

  const rows = section(page).locator('tr.risk-row');
  await expect(rows).toHaveCount(9);
  await expect(section(page).locator('thead th')).toHaveText(['Pull request', 'Author', 'Risk', 'Status', 'Updated']);
  await expect(prRow(page, 8)).toContainText('grace-long');
  await expect(prRow(page, 8)).toContainText('Not analysed');
  await expect(prRow(page, 9)).toContainText('Merged');
  await expect(prRow(page, 7).locator('.rbadge')).toHaveText('High');
  expect(syncs.length).toBe(1);  // the saved list was empty, so GitHub was read once

  // the author is in the database, not only on screen
  const saved = await (await page.request.get('/api/analysis/repo-pulls')).json();
  expect(saved.stale).toBe(false);
  expect(saved.items.find((p: { number: number }) => p.number === 4).author).toBe('carol-sec');

  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('carol');
  await expect(rows).toHaveCount(1);
  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('#7');
  await expect(rows).toHaveCount(1);
  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('nothing like this');
  await expect(section(page).getByText('No match')).toBeVisible();
  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('');

  await prRow(page, 8).click();
  await expect(prRow(page, 8)).toHaveAttribute('aria-expanded', 'true');
  await expect(section(page).getByText('Verixa has not analysed this pull request')).toBeVisible();
  await prRow(page, 1).click();
  await expect(section(page).getByText('charge succeeds with a valid card')).toBeVisible();  // the analysis in full

  // a reload shows the list at once from the tab's cache and does not read GitHub again (the list is fresh)
  await page.reload();
  await expect(rows).toHaveCount(9);
  expect(syncs.length).toBe(1);
  expect(problems).toEqual([]);
});

test('switching views and reloading never reads the graph or the log again', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.route('**/api/analysis/pull-requests/*/files', route => route.fulfill({ json: {
    head_sha: '0000007abcdef', same_commit: true, total_files: 1, shown_files: 1, scanned_for_imports: 1, edges: [],
    files: [{ path: 'src/payments/refund.ts', status: 'added', additions: 9, deletions: 0, risk: 'High', why: 'sensitive area: payments', folder: 'payments' }],
  } }));
  const graph = page.getByRole('tabpanel', { name: 'Dependency graph' });
  const files = count(page, /\/files$/);
  const logs = count(page, /\/log$/);
  await openRisk(page, 'Pull Requests');
  expect(files.length + logs.length).toBe(0);  // hidden views read nothing until they are opened

  await page.getByRole('tab', { name: 'Dependency graph' }).click();
  await expect(graph.locator('.node')).toHaveCount(1);
  await page.getByRole('tab', { name: 'Live runs and logs' }).click();
  await expect(page.locator('.stepper .step')).toHaveCount(8);
  for (const view of ['Overview', 'Dependency graph', 'Pull Requests', 'Live runs and logs', 'Dependency graph']) {
    await page.getByRole('tab', { name: view, exact: true }).click();
  }
  await expect(graph.locator('.node')).toHaveCount(1);
  expect([files.length, logs.length]).toEqual([1, 1]);

  // after a reload the graph comes back from this tab's cache, with no request and no loading message
  await page.reload();
  await expect(page.getByRole('tab', { name: 'Dependency graph' })).toHaveAttribute('aria-selected', 'true');
  await expect(graph.locator('.node')).toHaveCount(1);
  await expect(page.getByText('Reading the changed files from GitHub')).toHaveCount(0);
  expect(files.length).toBe(1);
  expect(problems).toEqual([]);
});

test('a pull request being analysed shows the processing view with the real agent steps, then its result', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Pull Requests');
  await expect(section(page).locator('tr.risk-row')).toHaveCount(9);

  // PR 106: every scripted model hangs, so the run stays in progress long enough to watch (tests/e2e/server.py)
  const body = JSON.stringify({
    action: 'opened', number: 106,
    pull_request: { number: 106, title: 'Every model hangs', html_url: 'https://github.com/demo/shop/pull/106',
                    head: { sha: '000006a' + 'a'.repeat(33) }, base: { ref: 'main' },
                    user: { login: 'webhook-author' }, state: 'open', updated_at: '2026-11-30T00:00:00Z' },
    repository: { full_name: 'demo/shop' },
  });
  const signature = 'sha256=' + crypto.createHmac('sha256', SECRET).update(body).digest('hex');
  expect((await page.request.post('/webhooks/github', { data: body, headers: {
    'content-type': 'application/json', 'x-github-event': 'pull_request', 'x-github-delivery': `t096-${Date.now()}`,
    'x-hub-signature-256': signature } })).status()).toBe(202);

  const proc = page.getByRole('region', { name: 'Verixa is analysing pull request 106' });
  await expect(proc).toBeVisible({ timeout: 15_000 });
  await expect(proc).toContainText('Every model hangs');
  await expect(proc.getByRole('list', { name: 'Agent activity' }).locator('li')).not.toHaveCount(0);
  await expect(proc).toContainText(/Analysis agent|GitHub|rules|Received/i);  // a real step text from backend/live.py
  // the delivery saved the pull request with its author before the agents finished
  await expect(prRow(page, 106)).toContainText('webhook-author');
  // a reload mid-run brings the processing view back: the server replays the run's steps to a new connection
  await page.reload();
  await expect(proc).toBeVisible({ timeout: 15_000 });
  await expect(proc.getByRole('list', { name: 'Agent activity' }).locator('li')).not.toHaveCount(0);
  expect(problems).toEqual([]);
});

test('negative: an account with no pull requests gets the empty list, no processing view and no GitHub read', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'other@verixa.dev', baseURL!);
  await openRisk(page, 'Pull Requests');
  await expect(section(page).getByText('No pull requests yet')).toBeVisible();
  await expect(page.locator('.proc')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('long test text wraps: the Tests chips and the Test Library name cells grow instead of clipping', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Overview');
  await rowOf(page, 1).first().click();
  await page.getByRole('button', { name: 'Open run log' }).click();
  const chip = page.locator('.rl-chips .tchip', { hasText: 'never charges the customer twice' });
  await expect(chip).toBeVisible();
  const fit = (sel: string) => page.locator(sel).first().evaluate(el => ({ h: el.clientHeight, sh: el.scrollHeight, sw: el.scrollWidth, w: el.clientWidth }));
  const c = await chip.evaluate(el => ({ h: el.clientHeight, sh: el.scrollHeight, sw: el.scrollWidth, w: el.clientWidth }));
  expect(c.h).toBeGreaterThan(30);                 // two lines, not a 26px pill
  expect(c.sh).toBeLessThanOrEqual(c.h + 1);       // nothing spills out
  expect(c.sw).toBeLessThanOrEqual(c.w + 1);

  const long = 'a declined card after a timeout and a duplicate click shows exactly one clear error message';
  await page.getByRole('button', { name: 'Test Library' }).click();
  await page.locator('input[type=file]').first().setInputFiles({ name: 'checkout.spec.ts', mimeType: 'text/plain', buffer: Buffer.from(
    `import { test, expect } from '@playwright/test';\n\ntest('${long}', async ({ page }) => {\n  await page.goto('/');\n  await expect(page).toHaveTitle(/Shop/);\n});\n\ntest('short name', async ({ page }) => {\n  await page.goto('/');\n});\n`) });
  const cell = page.getByRole('textbox', { name: 'Test case name' }).first();
  await expect(cell).toHaveValue(long);
  const t = await fit('textarea.cell.wrap');
  expect(t.h).toBeGreaterThan(40);                 // grew past one 38px line
  expect(t.sh).toBeLessThanOrEqual(t.h + 2);       // the whole name shows, nothing clipped
  expect(problems).toEqual([]);
});
