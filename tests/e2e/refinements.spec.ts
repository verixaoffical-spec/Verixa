/* T-098 on the real app: the Risk view tabs have a frosted glass indicator that glides to the selected tab, and Live
 * runs and logs lays out Results and Tests without empty space, so the whole view fits one screen at 1440x900.
 */
import { expect, test, type Page } from '@playwright/test';
import crypto from 'node:crypto';
import { closePages, openRisk, signIn } from './helpers';

test.afterEach(closePages);

const box = async (page: Page, sel: string) => (await page.locator(sel).first().boundingBox())!;

async function indicatorOn(page: Page, name: string) {
  const tab = page.locator('.rnav').getByRole('tab', { name, exact: true });
  await expect(tab).toHaveAttribute('aria-selected', 'true');
  await expect.poll(async () => {  // after the glide settles, the glass covers exactly the selected tab
    const [t, i] = [await tab.boundingBox(), await page.locator('.rnav-ind').boundingBox()];
    return t && i ? Math.max(Math.abs(t.x - i.x), Math.abs(t.width - i.width)) : 99;
  }).toBeLessThan(1.5);
}

test('the selected tab has a frosted glass indicator that glides to each tab, by mouse and by keyboard', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await openRisk(page, 'Pull Requests');
  const ind = page.locator('.rnav-ind');
  await expect(ind).toHaveCount(1);
  const look = await ind.evaluate(el => {
    const s = getComputedStyle(el);
    return { bg: s.backgroundImage, blur: s.backdropFilter || (s as unknown as Record<string, string>).webkitBackdropFilter, move: s.transitionProperty };
  });
  expect(look.blur).toContain('blur(');                        // frosted
  const colours = look.bg.match(/rgba?\([^)]*\)/g) ?? [];
  expect(colours.length).toBeGreaterThan(0);
  for (const c of colours) expect(c).toMatch(/^rgba\(1\d\d, \d+, 2\d\d, 0?\.\d+\)$/);  // the accent purple, every stop translucent
  expect(look.move).toContain('transform');                     // it glides

  for (const name of ['Overview', 'Live runs and logs', 'Dependency graph', 'Pull Requests']) {
    await page.locator('.rnav').getByRole('tab', { name, exact: true }).click();
    await indicatorOn(page, name);
  }
  await page.locator('.rnav').getByRole('tab', { name: 'Pull Requests' }).focus();
  await page.keyboard.press('End');
  await indicatorOn(page, 'Live runs and logs');
  // the selected tab itself is not painted solid any more: the glass behind it carries the colour
  expect(await page.locator('.rnav [aria-selected="true"]').evaluate(el => getComputedStyle(el).backgroundColor)).toBe('rgba(0, 0, 0, 0)');
  expect(problems).toEqual([]);
});

test('Live runs and logs fits one screen: log beside its checks, result beside tests, nothing removed', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.setViewportSize({ width: 1440, height: 900 });
  await openRisk(page, 'Live runs and logs');
  const panel = page.getByRole('tabpanel', { name: 'Live runs and logs' });
  await expect(panel.getByRole('heading', { name: 'Result and decision' })).toBeVisible();
  await expect(panel.getByText('Test before merging')).toBeVisible();          // the result is all still there
  await expect(panel.locator('.checks li').first()).toContainText('size: 4 file(s)');
  await expect(panel.getByText('Test execution is not built yet')).toBeVisible();

  const [log, rules] = [await box(page, '.livegrid > .rchart:first-child'), await box(page, '.livegrid > .rchart:last-child')];
  expect(Math.abs(log.height - rules.height)).toBeLessThan(2);                  // one row, no column hanging over space
  const [result, tests] = [await box(page, '.liveres > .rchart:first-child'), await box(page, '.liveres > .rchart:last-child')];
  expect(Math.abs(result.y - tests.y)).toBeLessThan(1);                         // side by side
  expect(Math.abs(result.height - tests.height)).toBeLessThan(2);
  expect(result.y).toBeGreaterThan(log.y + log.height);
  expect(tests.y + tests.height).toBeLessThanOrEqual(900);                      // the whole view in one screen

  // the run's status dot sits inside its pill (a global .dot rule used to pin it to the card's corner)
  const [pill, dot] = [await box(page, '.rlive .pill'), await box(page, '.rlive .pill .dot')];
  expect(dot.x).toBeGreaterThanOrEqual(pill.x);
  expect(dot.x + dot.width).toBeLessThanOrEqual(pill.x + pill.width);
  expect(problems).toEqual([]);
});

test('while a run streams in, the log keeps its room even though the checks card is still empty', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  // PR 106: every scripted model hangs, so the run stays in progress (tests/e2e/server.py)
  const body = JSON.stringify({ action: 'opened', number: 106, repository: { full_name: 'demo/shop' },
    pull_request: { number: 106, title: 'Every model hangs', head: { sha: '000006a' + 'a'.repeat(33) }, user: { login: 'webhook-author' } } });
  const signature = 'sha256=' + crypto.createHmac('sha256', 'e2e-only-webhook-secret-0123456789').update(body).digest('hex');
  expect((await page.request.post('/webhooks/github', { data: body, headers: { 'content-type': 'application/json',
    'x-github-event': 'pull_request', 'x-github-delivery': `t098-${Date.now()}`, 'x-hub-signature-256': signature } })).status()).toBe(202);
  await page.setViewportSize({ width: 1440, height: 900 });
  await openRisk(page, 'Live runs and logs');
  const pick = page.getByRole('tabpanel', { name: 'Live runs and logs' }).getByRole('combobox', { name: 'Pull request', exact: true });
  await expect(pick.locator('option', { hasText: '#106' })).toHaveCount(1, { timeout: 15_000 });
  await pick.selectOption({ label: '#106 · Every model hangs' });
  await expect(page.locator('.livegrid > .rchart.running')).toHaveCount(1, { timeout: 15_000 });
  expect((await box(page, '.livegrid > .rchart.running .console')).height).toBeGreaterThanOrEqual(359);

  // the status dot stays inside its pill in the light theme too, without the change list's white ring
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  expect(await page.locator('.rlive .pill .dot').evaluate(el => getComputedStyle(el).boxShadow)).not.toContain('255, 255, 255');
  expect(problems).toEqual([]);
});

test('with reduced motion the indicator jumps without a transition', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await openRisk(page, 'Overview');
  expect(await page.locator('.rnav-ind').evaluate(el => getComputedStyle(el).transitionDuration)).toBe('0s');
  await indicatorOn(page, 'Overview');
  expect(problems).toEqual([]);
});

test('negative: on a narrow screen the live view stacks into one column, with no sideways scroll', async ({ browser, baseURL }) => {
  const { page, problems } = await signIn(browser, 'demo@verixa.dev', baseURL!);
  await page.setViewportSize({ width: 820, height: 900 });
  await openRisk(page, 'Live runs and logs');
  const [result, tests] = [await box(page, '.liveres > .rchart:first-child'), await box(page, '.liveres > .rchart:last-child')];
  expect(tests.y).toBeGreaterThan(result.y + result.height - 1);               // stacked, not squeezed side by side
  expect(Math.abs(result.x - tests.x)).toBeLessThan(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(820);
  await indicatorOn(page, 'Live runs and logs');
  expect(problems).toEqual([]);
});
