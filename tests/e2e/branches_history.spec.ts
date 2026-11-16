/* T-099 on the real app (tests/e2e/server.py: #1 has 2 past defects in payments, #3 is at the repository root with
 * none, #2's lookups never answered; GitHub's list gives each pull request a source branch, #7 and #9 go into develop
 * and the rest into main). Defect history is shown apart from the stage's run status, and the Pull Requests section
 * is filtered by branch through the API.
 */
import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';
import { closePages, openRisk, signIn } from './helpers';

test.afterEach(closePages);

const live = (page: Page) => page.getByRole('tabpanel', { name: 'Live runs and logs' });
const historyStep = (page: Page) => live(page).locator('.step').filter({ hasText: 'Defect history' });
const section = (page: Page) => page.getByRole('tabpanel', { name: 'Pull Requests' });
const numbers = (page: Page) => section(page).locator('tr.risk-row .rpr-title b').allTextContents();

async function pick(page: Page, label: string) {
  await live(page).getByRole('combobox', { name: 'Pull request', exact: true }).selectOption({ label });
}

test('defect history shows what is known, and a finished run never shows a stage as waiting', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Live runs and logs');

  await pick(page, '#3 · Fix a typo in the footer');  // no history: a result, not a wait
  await expect(historyStep(page).locator('.h')).toHaveText('No defect history');
  await expect(historyStep(page).locator('.h')).toHaveClass(/\bnone\b/);
  await expect(historyStep(page).locator('.t')).not.toHaveText('waiting');
  await expect(live(page).locator('.stepper')).not.toContainText('waiting');

  await pick(page, '#1 · Refactor checkout session');
  await expect(historyStep(page).locator('.h')).toHaveText('2 past defects');
  await expect(historyStep(page).locator('.h')).toHaveAttribute('aria-label', 'Defect history: 2 past defects in payments');
  await expect(historyStep(page).locator('.h')).toHaveClass(/\bfound\b/);

  await pick(page, '#2 · Update profile page');  // negative: lookups that never answered are not "no history"
  await expect(historyStep(page).locator('.h')).toHaveText('History unknown');
  expect(problems).toEqual([]);
});

test('while a run is going its stages still wait, and no defect history is claimed before it is known', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  // PR 106: every scripted model hangs, so the run stays in progress after its GitHub stages
  const body = JSON.stringify({ action: 'opened', number: 106, repository: { full_name: 'demo/shop' },
    pull_request: { number: 106, title: 'Every model hangs', head: { sha: '000006a' + 'a'.repeat(33), ref: 'feature/hang' },
      base: { ref: 'main' }, user: { login: 'webhook-author' } } });
  const signature = 'sha256=' + crypto.createHmac('sha256', 'e2e-only-webhook-secret-0123456789').update(body).digest('hex');
  expect((await page.request.post('/webhooks/github', { data: body, headers: { 'content-type': 'application/json',
    'x-github-event': 'pull_request', 'x-github-delivery': `t099-${Date.now()}`, 'x-hub-signature-256': signature } })).status()).toBe(202);
  await openRisk(page, 'Live runs and logs');
  const prs = live(page).getByRole('combobox', { name: 'Pull request', exact: true });
  await expect(prs.locator('option', { hasText: '#106' })).toHaveCount(1, { timeout: 15_000 });
  await pick(page, '#106 · Every model hangs');
  await expect(live(page).locator('.step.c')).toHaveCount(1, { timeout: 15_000 });
  await expect(historyStep(page)).toHaveClass(/\bd\b/);                 // its lookups ran: the stage itself is done
  await expect(live(page).locator('.step', { hasText: 'Saved' }).locator('.t')).toHaveText('waiting');  // genuinely waiting
  await expect(historyStep(page).locator('.h')).toHaveCount(0);         // the saved row is not this run's yet

  // the webhook saved the pull request's branches too
  const saved = await (await page.request.get('/api/analysis/repo-pulls?branch=feature/hang')).json();
  expect(saved.items.map((p: { number: number; base_ref: string }) => [p.number, p.base_ref])).toEqual([[106, 'main']]);
  expect(problems).toEqual([]);
});

test('Pull Requests show each source and target branch and are filtered by the selected branch', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  const asked: string[] = [];
  page.on('request', r => { if (/\/api\/analysis\/repo-pulls\?branch=/.test(r.url())) asked.push(decodeURIComponent(r.url())); });
  await openRisk(page, 'Pull Requests');
  const rows = section(page).locator('tr.risk-row');
  await expect(rows).not.toHaveCount(0);
  const seven = rows.filter({ has: page.locator('.rpr-title b:text-is("#7")') });
  await expect(seven.locator('.prs-branches')).toHaveAttribute('aria-label', 'from branch feature/refunds into develop');
  await expect(seven.locator('.prs-ref')).toHaveText(['feature/refunds', 'develop']);

  const branch = section(page).getByRole('combobox', { name: 'Branch' });
  await expect(branch.locator('option').first()).toHaveText('All branches');
  await expect(branch.locator('option', { hasText: 'develop' })).toHaveText('develop · 2 PRs');
  await expect(branch.locator('option', { hasText: 'feature/checkout' })).toHaveText('feature/checkout · 2 PRs');

  await branch.selectOption('develop');  // into develop
  await expect.poll(() => numbers(page)).toEqual(['#9', '#7']);
  await expect(seven.locator('.prs-ref.on')).toHaveText('develop');      // the selected branch is marked
  expect(asked.some(u => u.endsWith('branch=develop'))).toBe(true);      // filtered by the API, not only on screen

  await branch.selectOption('feature/checkout');  // from feature/checkout
  await expect.poll(() => numbers(page)).toEqual(['#8', '#1']);
  await expect(seven).toHaveCount(0);  // negative: a pull request of another branch is not mixed in

  // search and expand still work inside a branch, and the analysis opened is that pull request's own
  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('session');
  await expect.poll(() => numbers(page)).toEqual(['#1']);
  await rows.first().click();
  await expect(section(page).locator('.rdetail')).toContainText('rewrites how a checkout session is charged');
  await section(page).getByRole('searchbox', { name: 'Search pull requests' }).fill('');

  await branch.selectOption('');
  await expect.poll(async () => (await numbers(page)).length).toBeGreaterThanOrEqual(9);
  expect(problems).toEqual([]);
});
