/* T-089 Premium Risk screens, on the real app with the seeded demo data (GitHub and the models are scripted).
 *  - Overview: the Analyses vs flagged risk area chart counts the saved analyses, compares a day on hover, switches range;
 *    the risk tiles carry a share ring that matches the feed's counts.
 *  - Light theme: an expanded pull request sits on the page background; the Dependency graph canvas is white.
 *    Dark theme keeps both as they were.
 *  - A live run: the processing view shows the working agent's own scene (one at a time, with a transition), moving from
 *    the Manager to the Analysis agent as the real steps arrive. Live runs and logs follows the new pull request by itself,
 *    its stages turn green one after another from the socket, and Defect history and CI end grey ("not covered").
 *  Negative: a pull request with no saved steps marks nothing green or grey and its track stays empty; no Test agent
 *  scene is shown, because the Test agent sends no steps yet.
 */
import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';
import { closePages, openRisk, signIn } from './helpers';

test.afterEach(closePages);

const FILES = {
  head_sha: '0000007' + 'a'.repeat(33), total_files: 2, shown_files: 2,
  files: [
    { path: 'src/api/login.ts', status: 'modified', additions: 30, deletions: 4, risk: 'High', why: 'auth', folder: 'src/api' },
    { path: 'src/auth/token.ts', status: 'modified', additions: 12, deletions: 2, risk: 'Medium', why: 'auth', folder: 'src/auth' },
  ],
  edges: [['src/api/login.ts', 'src/auth/token.ts']],
};
const style = (page: Page, sel: string, prop: string) =>
  page.locator(sel).first().evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
const theme = (page: Page, t: 'light' | 'dark') => page.evaluate(t => document.documentElement.setAttribute('data-theme', t), t);

test('Overview: the trend chart counts the saved analyses, compares a day on hover and switches range', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Overview');
  const feed = await (await page.request.get('/api/analysis/pull-requests?limit=200')).json();

  // expected counts per local day, computed in the page so the time zone matches
  const expected = await page.evaluate(items => {
    const now = new Date();
    const days = (n: number) => Array.from({ length: n }, (_, i) => new Date(now.getFullYear(), now.getMonth(), now.getDate() - (n - 1 - i)).toDateString());
    const count = (n: number) => {
      const keys = new Set(days(n));
      const rows = items.filter((r: { created_at: string | null }) => r.created_at && keys.has(new Date(r.created_at).toDateString()));
      return { all: rows.length, flagged: rows.filter((r: { risk_label: string | null }) => r.risk_label === 'High' || r.risk_label === 'Medium').length };
    };
    const today = items.filter((r: { created_at: string | null }) => r.created_at && new Date(r.created_at).toDateString() === now.toDateString());
    return { d14: count(14), d30: count(30), today: { all: today.length,
             flagged: today.filter((r: { risk_label: string | null }) => r.risk_label === 'High' || r.risk_label === 'Medium').length } };
  }, feed.items);

  const chart = page.getByRole('region', { name: 'Analyses and flagged risk' });
  await expect(chart.getByRole('heading', { name: 'Analyses vs flagged risk' })).toBeVisible();
  await expect(chart.locator('.rtrend-total')).toHaveText(String(expected.d14.all));
  await expect(chart.locator('.rtrend-sum')).toContainText(`${expected.d14.flagged} flagged`);
  await expect(chart.locator('.rtrend-line')).toHaveCount(2);
  await expect(chart.locator('.rtrend-area')).toHaveCount(2);
  expect((await chart.locator('svg.rtrend-svg').boundingBox())!.width).toBeGreaterThan(600);  // not the 16px icon size

  // hover the last day (today): the guide and the tooltip compare both series
  const plot = chart.locator('.rtrend-plot');
  await plot.scrollIntoViewIfNeeded();  // the hero and goal cards sit above it
  const box = (await plot.boundingBox())!;
  await page.mouse.move(box.x + box.width - 12, box.y + box.height / 2);
  const tip = chart.locator('.rtrend-tip');
  await expect(tip).toBeVisible();
  await expect(chart.locator('.rtrend-guide circle')).toHaveCount(2);
  await expect(tip.locator('span', { hasText: 'Analyses' }).locator('em')).toHaveText(String(expected.today.all));
  await expect(tip.locator('span', { hasText: 'Flagged' }).locator('em')).toHaveText(String(expected.today.flagged));
  await page.mouse.move(box.x - 40, box.y - 40);
  await expect(tip).toHaveCount(0);

  // the keyboard reaches the same comparison
  await plot.focus();
  await page.keyboard.press('End');
  await expect(tip).toBeVisible();

  await chart.getByRole('button', { name: '30d' }).click();
  await expect(chart.getByRole('button', { name: '30d' })).toHaveAttribute('aria-pressed', 'true');
  await expect(chart.locator('.rtrend-total')).toHaveText(String(expected.d30.all));
  await expect(chart.locator('.rtrend-sum')).toContainText('in the last 30 days');

  // share rings: every tile's percentage is its count over the feed's total (the total tile shows the scored share)
  const c = feed.counts;
  const pct = (n: number) => `${c.total ? Math.round((n / c.total) * 100) : 0}%`;
  await expect(page.locator('.risk-stat .risk-ring b')).toHaveText([pct(c.scored ?? 0), pct(c.High ?? 0), pct(c.Medium ?? 0), pct(c.Low ?? 0)]);
  expect((await page.locator('.risk-ring svg').first().boundingBox())!.width).toBe(100);
  expect(problems).toEqual([]);
});

test('light theme: pull request detail on the page background, Dependency graph on white; dark unchanged', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.route('**/api/analysis/pull-requests/*/files', route => route.fulfill({ json: FILES }));
  await openRisk(page, 'Pull Requests');
  const section = page.getByRole('tabpanel', { name: 'Pull Requests' });
  await section.locator('tr.risk-row').first().click();
  const detail = section.locator('td.rdetail');
  await expect(detail).toBeVisible();

  await theme(page, 'light');
  await expect.poll(() => style(page, '[aria-label="Pull Requests on GitHub"] td.rdetail', 'background-color')).toBe('rgb(244, 244, 248)');
  await detail.hover();  // the row hover must not paint it white again
  await expect.poll(() => style(page, '[aria-label="Pull Requests on GitHub"] td.rdetail', 'background-color')).toBe('rgb(244, 244, 248)');
  expect(await style(page, 'body', 'background-color')).toBe('rgb(244, 244, 248)');  // the same as the page

  await page.getByRole('tab', { name: 'Dependency graph', exact: true }).click();
  const vp = page.getByLabel(/^Dependency graph of PR/);
  await expect(vp.locator('.node')).toHaveCount(2);
  await expect.poll(() => style(page, '.vp', 'background-color')).toBe('rgb(255, 255, 255)');
  expect(await style(page, '.vp .node', 'background-color')).toBe('rgb(255, 255, 255)');
  expect(await style(page, '.vp .nm b', 'color')).toBe('rgb(11, 11, 20)');  // dark text on the white canvas

  await theme(page, 'dark');  // negative: the dark theme keeps the black canvas and an unpainted detail row
  await expect.poll(() => style(page, '.vp', 'background-color')).toBe('rgb(0, 0, 0)');
  await page.getByRole('tab', { name: 'Pull Requests', exact: true }).click();
  expect(await style(page, '[aria-label="Pull Requests on GitHub"] td.rdetail', 'background-color')).not.toBe('rgb(244, 244, 248)');
  expect(problems).toEqual([]);
});

test('a live run: each agent has its own scene, Live runs follows it, stages fill from the socket, history and CI end grey', async ({ browser, baseURL }) => {
  test.setTimeout(120_000);  // the first agent run of a fresh server also loads the model library
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Pull Requests');
  // PR 106: every scripted model hangs, so the run stays with the Analysis agent for a few seconds before it is saved
  const body = JSON.stringify({ action: 'opened', number: 106, repository: { full_name: 'demo/shop' },
    pull_request: { number: 106, title: 'Every model hangs', head: { sha: '000006b' + 'b'.repeat(33), ref: 'feature/hang' },
      base: { ref: 'main' }, user: { login: 'webhook-author' } } });
  const signature = 'sha256=' + crypto.createHmac('sha256', 'e2e-only-webhook-secret-0123456789').update(body).digest('hex');
  // every view stays mounted, so Live runs and logs updates while hidden: record each change of its green stage count
  await page.evaluate(() => {
    const w = window as unknown as { counts: number[] };
    const panel = document.querySelector('[aria-label="Live runs and logs"]')!;
    w.counts = [];
    new MutationObserver(() => {
      const n = panel.querySelectorAll('.stepper .step.d').length;
      if (w.counts[w.counts.length - 1] !== n) w.counts.push(n);
    }).observe(panel, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
  });
  expect((await page.request.post('/webhooks/github', { data: body, headers: { 'content-type': 'application/json',
    'x-github-event': 'pull_request', 'x-github-delivery': `t089-${Date.now()}`, 'x-hub-signature-256': signature } })).status()).toBe(202);

  const proc = page.getByRole('tabpanel', { name: 'Pull Requests' }).locator('section.proc');  // the Overview shows it too
  await expect(proc).toBeVisible({ timeout: 15_000 });
  // exactly one scene is on, the one named by the processing view, and the strip lights the same agent
  const agent = async () => proc.getAttribute('data-agent');
  await expect(proc.locator('.ag-scene.on')).toHaveCount(1);
  await expect.poll(agent, { timeout: 15_000 }).toBe('analysis');   // GitHub reads, rules and the model call
  await expect(proc.locator('.ag-scene.on')).toHaveClass(/\bag-analysis\b/);
  await expect(proc.locator('.ag-pill.on')).toHaveText(/Analysis/);
  await expect(proc.locator('.ag-test.on')).toHaveCount(0);          // negative: no Test agent steps exist yet
  // the scenes cross-fade, and each agent's scene moves in its own way
  expect(parseFloat(await style(page, '.ag-scene', 'transition-duration'))).toBeGreaterThan(0);
  expect(await proc.locator('.ag-sweep').evaluate(el => getComputedStyle(el).animationName)).toBe('ag-turn');
  expect(await proc.locator('.ag-dial').evaluate(el => getComputedStyle(el).animationName)).toBe('ag-score');
  expect(await proc.locator('.ag-cases i').first().evaluate(el => getComputedStyle(el).animationName)).toBe('ag-pass');
  const leave = await proc.locator('.ag-manager').evaluate(el => getComputedStyle(el).transform);
  const flip = await proc.locator('.ag-test').evaluate(el => getComputedStyle(el).transform);
  expect(leave).not.toBe('none');
  expect(flip).not.toBe(leave);  // a different way in for each agent

  // Live runs and logs follows the new pull request by itself, while its run is going
  await page.getByRole('tab', { name: 'Live runs and logs', exact: true }).click();
  const live = page.getByRole('tabpanel', { name: 'Live runs and logs' });
  await expect(live.getByRole('combobox', { name: 'Pull request', exact: true }).locator('option:checked')).toHaveText(/#106/, { timeout: 15_000 });
  await expect(live.locator('.pill', { hasText: 'Finished' })).toHaveCount(1, { timeout: 30_000 });
  // the stages arrived over time from the socket, not all at once: the green count rose through values in between
  const counts = await page.evaluate(() => (window as unknown as { counts: number[] }).counts);
  const rising = counts.filter(n => n > 0 && n < 8);
  expect(rising.length, `green stage counts seen: ${counts.join(',')}`).toBeGreaterThanOrEqual(2);
  // finished: seven stages reported (history among them, grey); CI sent no step here (AGENT_CI_CHECK=0), so it is skipped
  await expect(live.locator('.stepper .step.d')).toHaveCount(7);

  // finished: history and CI grey "not covered", every other stage green with its time, the track full
  const step = (name: string) => live.locator('.stepper .step', { hasText: name });
  await expect(step('Defect history')).toHaveClass(/\bx\b/);
  await expect(step('Defect history').locator('.t')).toHaveText('not covered');
  await expect(step('CI')).toHaveClass(/\bx\b/);
  await expect(step('CI').locator('.t')).toHaveText('not covered');
  for (const name of ['Received', 'Read changes', 'Rules', 'Model', 'Manager', 'Saved']) {
    await expect(step(name)).toHaveClass(/\bd\b/);
    await expect(step(name)).not.toHaveClass(/\bx\b/);
    await expect(step(name).locator('.t')).toHaveText(/^\d\d:\d\d:\d\d$/);
  }
  // every line between stages is drawn; the ones into and out of Defect history and CI are grey
  await expect(live.locator('.stepper-seg.on')).toHaveCount(7);
  await expect(live.locator('.stepper-seg.grey')).toHaveCount(3);
  await expect(live.locator('.stepper-seg.grey')).toHaveCount(3);
  expect(await live.locator('.stepper-seg.grey b').first().evaluate(el => getComputedStyle(el).backgroundImage)).toBe('none');
  expect(problems).toEqual([]);
});

test('negative: a pull request with no saved steps has no green or grey stage and an empty track', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Live runs and logs');
  const live = page.getByRole('tabpanel', { name: 'Live runs and logs' });
  await live.getByRole('combobox', { name: 'Pull request', exact: true }).selectOption({ label: '#3 · Fix a typo in the footer' });
  await expect(live.getByText('No saved steps for this pull request')).toBeVisible();
  await expect(live.locator('.stepper .step.d')).toHaveCount(0);
  await expect(live.locator('.stepper .step.x')).toHaveCount(0);
  await expect(live.locator('.stepper')).not.toContainText('not covered');
  await expect(live.locator('.stepper-seg.on')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('follow-up: Analyse now inside a pull request, the last run on the webhook chip, day bars, skeleton loading', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  // skeleton while the saved lists are read (the answer is held back a moment so it can be seen)
  let held = false;  // only the first read is held back
  await page.route('**/api/analysis/pull-requests?limit=200', async route => {
    if (!held) { held = true; await new Promise(r => setTimeout(r, 5000)); }  // long enough to open the tab on a slow run
    await route.continue();
  });
  await page.goto('/verixa_prototype.html#risk');
  await expect(page.getByRole('heading', { name: 'Risk Analysis' })).toBeVisible({ timeout: 15_000 });
  await page.getByRole('tab', { name: 'Overview', exact: true }).click();
  await expect(page.getByRole('status', { name: "Reading the agent's assessments" })).toBeVisible();
  await expect(page.getByRole('status', { name: "Reading the agent's assessments" }).locator('.skel-row')).toHaveCount(5);

  // the webhook chip says when the newest analysis ran
  const feed = await (await page.request.get('/api/analysis/pull-requests?limit=200')).json();
  await expect(page.locator('.rpage-head .chip').first()).toContainText(/Webhook verified · (just now|\d+[mhd] ago)/);

  // the hero shows the last 7 days while fewer than two weeks have analyses (the seed's are all recent)
  const hero = page.getByRole('region', { name: 'Analyses' });
  await expect(hero.locator('.ov-kicker').nth(1)).toHaveText('Analyses per day, last 7 days');
  await expect(hero.locator('.ov-bar')).toHaveCount(7);
  const today = await page.evaluate(items => items.filter((r: { created_at: string | null }) =>
    r.created_at && new Date(r.created_at).toDateString() === new Date().toDateString()).length, feed.items);
  await expect(hero.locator('.ov-bar.now .ov-bar-n')).toHaveText(String(today));

  // a pull request Verixa never analysed has Analyse now inside it
  await page.getByRole('tab', { name: 'Pull Requests', exact: true }).click();
  const section = page.getByRole('tabpanel', { name: 'Pull Requests' });
  const row = section.locator('tr.risk-row', { hasText: 'Not analysed' }).first();
  await row.click();
  await expect(section.locator('td.rdetail').getByRole('button', { name: 'Analyse now' })).toBeEnabled();
  await expect(section.locator('td.rdetail')).toContainText('or right here');

  // negative: the seed's pull requests were all updated days ago, so no "commits Verixa did not receive" notice
  await expect(section.locator('.prs-missed')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('missed commits: an open pull request whose new commit GitHub has but Verixa never analysed is called out', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  // GitHub's list says PR 7 got a new commit 10 minutes ago that no analysis has (the webhook never delivered it)
  await page.route('**/api/analysis/repo-pulls*', async route => {
    const json = await (await route.fetch()).json();
    for (const p of json.items) if (p.number === 7) Object.assign(p, { state: 'open', head_sha: 'f'.repeat(40), updated_at: new Date(Date.now() - 10 * 60_000).toISOString() });
    await route.fulfill({ json });
  });
  await openRisk(page, 'Pull Requests');
  const notice = page.getByRole('tabpanel', { name: 'Pull Requests' }).locator('.prs-missed');
  await expect(notice).toBeVisible();
  await expect(notice).toContainText('GitHub has a commit Verixa did not receive');
  await expect(notice).toContainText('#7');
  await expect(notice.getByRole('button', { name: 'Analyse #7' })).toBeEnabled();
  expect(problems).toEqual([]);
});
