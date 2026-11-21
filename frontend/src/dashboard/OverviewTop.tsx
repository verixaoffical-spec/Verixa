/* T-089 The Overview's top row, laid out like the reference dashboard: a hero card (total, change against the week
 * before, a progress bar and capsule bars per week, the current week lit) and an Agents card beside it. Every number is
 * counted from the saved analyses; each agent's state is what is built and what the live socket reports.
 */
import type { CSSProperties, ReactNode } from 'react';
import type { Assessment, RiskFeed } from './api';
import type { AgentName } from './AgentScene';

const DAY = 86_400_000;

/** Analyses per week (weeks start on Monday), oldest first, for the last `weeks` weeks. */
export function perWeek(items: Assessment[], weeks = 6, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const monday = new Date(today.getTime() - ((today.getDay() + 6) % 7) * DAY);
  const out = Array.from({ length: weeks }, (_, i) => {
    const start = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() - 7 * (weeks - 1 - i));
    return { start, label: start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), n: 0 };
  });
  for (const row of items) {
    if (!row.created_at) continue;
    const t = new Date(row.created_at).getTime();
    const slot = [...out].reverse().find(w => t >= w.start.getTime());
    if (slot && t < monday.getTime() + 7 * DAY) slot.n += 1;
  }
  return out;
}

/** Analyses per local day for the last `days` days, oldest first: the hero's bars while there is little history. */
export function perDayBars(items: Assessment[], days = 7, now = new Date()) {
  const out = Array.from({ length: days }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (days - 1 - i));
    return { key: d.toDateString(), label: d.toLocaleDateString(undefined, { weekday: 'short' }),
             full: d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' }), n: 0 };
  });
  for (const row of items) {
    if (!row.created_at) continue;
    const slot = out.find(d => d.key === new Date(row.created_at as string).toDateString());
    if (slot) slot.n += 1;
  }
  return out;
}

function lastDays(items: Assessment[], from: number, to: number, now = Date.now()) {
  return items.filter(r => r.created_at && now - new Date(r.created_at).getTime() >= from * DAY
                                         && now - new Date(r.created_at).getTime() < to * DAY).length;
}

function Hero({ items, counts }: { items: Assessment[]; counts: RiskFeed['counts'] }) {
  // T-089: weeks once there are two or more weeks with analyses; until then the last 7 days, so the bars are not mostly empty
  const byWeek = perWeek(items);
  const daily = byWeek.filter(w => w.n > 0).length < 2;
  const bars = daily ? perDayBars(items).map(d => ({ key: d.key, label: d.label, title: `${d.full}: ${d.n} analyses`, n: d.n }))
                     : byWeek.map(w => ({ key: w.label, label: w.label, title: `Week of ${w.label}: ${w.n} analyses`, n: w.n }));
  const max = Math.max(1, ...bars.map(w => w.n));
  const week = lastDays(items, 0, 7), before = lastDays(items, 7, 14);
  const change = before ? Math.round(((week - before) / before) * 100) : null;
  const total = counts.total ?? 0, scored = counts.scored ?? 0;
  const pct = total ? Math.round((scored / total) * 100) : 0;
  return (
    <section className="rcard ov-hero" aria-label="Analyses">
      <div className="ov-hero-main">
        <p className="ov-kicker">Total analyses</p>
        <b className="ov-big">{items.length}</b>
        <p className="ov-delta">
          {change === null ? <span className="ov-pill">{week} this week</span>
            : <span className={'ov-pill' + (change < 0 ? ' down' : '')}>{change >= 0 ? '↑' : '↓'} {Math.abs(change)}%</span>}
          <span className="muted">{change === null ? 'one per analysed commit' : 'than the week before'}</span>
        </p>
        <div className="ov-progress" role="img" aria-label={`${pct}% of ${total} pull requests scored`}>
          <i style={{ width: pct + '%' }}></i>
        </div>
        <p className="ov-progress-cap muted">{pct}% of {total} pull request{total === 1 ? '' : 's'} scored</p>
      </div>
      <div className="ov-weeks" aria-label={daily ? 'Analyses per day' : 'Analyses per week'}>
        <p className="ov-kicker">{daily ? 'Analyses per day, last 7 days' : 'Analyses per week'}</p>
        <div className="ov-bars" style={{ gridTemplateColumns: `repeat(${bars.length}, minmax(0,1fr))` }}>
          {bars.map((w, i) => (
            <div key={w.key} className={'ov-bar' + (i === bars.length - 1 ? ' now' : '')} title={w.title}>
              <span className="ov-bar-n">{w.n}</span>
              <span className="ov-cap" style={{ '--k': Math.max(0.07, w.n / max), '--d': `${i * 70}ms` } as CSSProperties}></span>
              <span className="ov-bar-x">{w.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const AGENT_ROWS: { key: AgentName; name: string; what: string; icon: ReactNode }[] = [
  { key: 'manager', name: 'Manager agent', what: 'Validates every output, retries up to 3 times.',
    icon: <svg viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 4.4-3 8.3-7 9.5C8 19.3 5 15.4 5 11V6z" /><path d="M9 12l2 2 4-4" /></svg> },
  { key: 'analysis', name: 'Analysis agent', what: 'Scores every pull request GitHub delivers.',
    icon: <svg viewBox="0 0 24 24"><path d="M4 18a8 8 0 1 1 16 0" /><path d="M12 18l4-6" /></svg> },
  { key: 'test', name: 'Test agent', what: 'Runs the relevant tests on staging. Deliverable 3, not built yet.',
    icon: <svg viewBox="0 0 24 24"><path d="M8 5.5v13l10.5-6.5z" /></svg> },
];

function Agents({ ready, working }: { ready: boolean; working: AgentName | null }) {
  const on = (k: AgentName) => k === 'manager' || (k === 'analysis' && ready);  // the Test agent is not built yet
  return (
    <section className="rcard ov-agents" aria-label="Agents">
      <header><h2>Agents</h2><span className="ov-on">{AGENT_ROWS.filter(a => on(a.key)).length} on</span></header>
      <ul>
        {AGENT_ROWS.map(a => (
          <li key={a.key} className={a.key + (working === a.key ? ' working' : '')}>
            <span className="ov-ico" aria-hidden="true">{a.icon}</span>
            <span className="ov-txt"><b>{a.name}{working === a.key && <em>working</em>}</b><small>{a.what}</small></span>
            <span className={'ov-switch' + (on(a.key) ? ' on' : '')} role="img" aria-label={on(a.key) ? 'On' : 'Off'}><i></i></span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function OverviewTop({ items, counts, ready, working }:
  { items: Assessment[]; counts: RiskFeed['counts']; ready: boolean; working: AgentName | null }) {
  return (
    <div className="ov-top">
      <Hero items={items} counts={counts} />
      <Agents ready={ready} working={working} />
    </div>
  );
}
