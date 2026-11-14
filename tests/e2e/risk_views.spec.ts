/* T-038: the Dependency graph and Live runs views of Risk Analysis, on the real app with the seeded demo data.
 * The log view reads the e2e server's real trace file, which this test writes. The graph's GitHub read cannot work
 * here (the seeded token is a placeholder GitHub refuses), so that real refusal is the negative case, and the drawing
 * itself is checked with a scripted /files answer in the exact shape tests/test_pr_views.py proves the backend returns.
 */
import fs from 'fs';
import { expect, test, type Page } from '@playwright/test';
import { closePages, openRisk, rowOf, signIn, tracePath } from './helpers';

test.afterEach(closePages);

const FILES = {
  head_sha: '0000001abcdef', same_commit: true, total_files: 4, shown_files: 4, scanned_for_imports: 3,
  files: [
    { path: 'src/api/login.ts', status: 'modified', additions: 30, deletions: 4, risk: 'High', why: 'sensitive area: login', folder: 'src/api' },
    { path: 'src/auth/token.ts', status: 'added', additions: 80, deletions: 0, risk: 'High', why: 'sensitive area: token', folder: 'src/auth' },
    { path: 'src/cart/total.ts', status: 'modified', additions: 5, deletions: 5, risk: 'Medium', why: 'touches cart', folder: 'src/cart' },
    { path: 'README.md', status: 'modified', additions: 1, deletions: 1, risk: 'Low', why: 'test or documentation file', folder: '(root)' },
  ],
  edges: [['src/api/login.ts', 'src/auth/token.ts'], ['src/api/login.ts', 'src/cart/total.ts']],
};

async function openTab(page: Page, name: string) {
  await openRisk(page);
  await page.getByRole('tab', { name }).click();
}

test('the graph draws every changed file with its risk, imports, search and details', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.route('**/api/analysis/pull-requests/*/files', route => route.fulfill({ json: FILES }));
  await openTab(page, 'Dependency graph');

  const graph = page.getByLabel(/^Dependency graph of PR/);
  await expect(graph.locator('.node')).toHaveCount(4);
  await expect(graph.locator('.e-imp')).toHaveCount(2);
  await expect(graph.locator('.lane')).toHaveCount(4);  // one lane per folder
  await expect(page.getByText('4 changed files in 4 folders · 2 imports between them')).toBeVisible();

  // importer sits left of what it imports
  const x = async (name: string) => (await graph.getByRole('button', { name: new RegExp(`^${name}`) }).boundingBox())!.x;
  expect(await x('login.ts')).toBeLessThan(await x('token.ts'));

  // search highlights the match
  await page.getByLabel('Find a file').fill('cart');
  await expect(graph.locator('.node.match')).toHaveCount(1);
  await page.getByLabel('Find a file').fill('');

  // a click opens the details, with what it imports
  await graph.getByRole('button', { name: 'login.ts, High risk' }).click();
  const details = page.getByLabel('File details');
  await expect(details).toContainText('src/api/login.ts');
  await expect(details).toContainText('sensitive area: login');
  await expect(details.locator('.ins-two')).toContainText('token.ts, total.ts');
  await expect(graph.locator('.e-imp.hi')).toHaveCount(2);

  // Hide Low removes the README, and the file list holds the same files
  await page.getByRole('button', { name: 'Hide Low' }).click();
  await expect(graph.locator('.node')).toHaveCount(3);
  await expect(page.getByLabel('Changed files').getByRole('button')).toHaveCount(4);
  expect(problems).toEqual([]);
});

test('negative: when GitHub refuses, the graph says so instead of drawing anything', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openTab(page, 'Dependency graph');  // real call: GitHub refuses the seeded placeholder token
  const graph = page.getByLabel(/^Dependency graph of PR/);
  await expect(graph.getByRole('alert')).toContainText('Could not draw the graph', { timeout: 30_000 });
  await expect(graph.locator('.node')).toHaveCount(0);
  expect(problems.filter(p => !/status of 50\d|Failed to load resource/.test(p))).toEqual([]);
});

test('the live view shows a saved run: stages, log, filter, checks and decision', async ({ browser, baseURL }) => {
  const at = (s: number) => new Date(Date.UTC(2026, 10, 14, 10, 0, s)).toISOString();
  const pr = 'demo/shop#7';
  fs.appendFileSync(tracePath('verixa-e2e'), [
    { at: at(0), run_id: null, pr_id: pr, event: 'service.delivery', action: 'opened' },
    { at: at(1), run_id: 'abcd1234', pr_id: pr, event: 'run.start' },
    { at: at(2), run_id: 'abcd1234', pr_id: pr, event: 'github.pr_read', files: 4 },
    { at: at(3), run_id: 'abcd1234', pr_id: pr, event: 'rules.scored', risk_label: 'High', score: 7 },
    { at: at(4), run_id: 'abcd1234', pr_id: pr, event: 'manager.decided', status: 'approved', risk_label: 'High' },
    { at: at(5), run_id: null, pr_id: pr, event: 'service.saved', state: 'scored' },
  ].map(l => JSON.stringify(l)).join('\n') + '\n');

  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page);
  await rowOf(page, 7).first().click();
  await page.getByRole('button', { name: 'Open run log' }).click();

  const steps = page.locator('.stepper .step');
  await expect(steps).toHaveCount(8);
  await expect(page.locator('.stepper .step.d')).toHaveCount(5);  // received, changes, rules, manager, saved
  await expect(steps.filter({ hasText: 'Model' })).toHaveClass(/\bw\b/);  // no model step arrived, so not marked done
  await expect(page.locator('.console .ln')).toHaveCount(6);
  await expect(page.locator('.console')).toContainText('Risk rules scored it High (7 points)');
  await page.getByRole('group', { name: 'Filter log' }).getByRole('button', { name: 'Rules' }).click();
  await expect(page.locator('.console .ln')).toHaveCount(1);
  await expect(page.getByText('Test before merging')).toBeVisible();
  await expect(page.locator('.checks li').first()).toContainText('size: 4 file(s)');
  expect(problems).toEqual([]);
});

test('negative: a PR with no saved steps says so, and nothing is marked done', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page);
  await rowOf(page, 3).first().click();
  await page.getByRole('button', { name: 'Open run log' }).click();
  await expect(page.getByText('No saved steps for this pull request')).toBeVisible();
  await expect(page.locator('.stepper .step.d')).toHaveCount(0);
  expect(problems).toEqual([]);
});
