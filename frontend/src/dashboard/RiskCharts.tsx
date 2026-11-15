/* Charts for Risk Analysis (T-036, prompt §8 A). Every value comes from /api/analysis/pull-requests, nothing is
 * invented. Design follows the approved prototype: risk shapes (triangle, diamond, circle) plus words, never colour
 * alone; each chart has a legend, hover/focus details, and the per-day chart can be read as a table.
 */
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import type { Assessment, RiskFeed, RiskLabel } from './api';

export const RISKS: RiskLabel[] = ['High', 'Medium', 'Low'];
const FILL: Record<RiskLabel, string> = { High: '#d03b3b', Medium: '#fab219', Low: '#31c47f' };  // validated (dataviz)

export function Glyph({ label }: { label: RiskLabel }) {
  return <i className={'rglyph ' + label.toLowerCase()} aria-hidden="true"></i>;
}

/** The newest row of each pull request (the feed is newest first). */
export function latestPerPr(items: Assessment[]): Assessment[] {
  const seen = new Set<number>();
  return items.filter(row => !seen.has(row.pr_number) && seen.add(row.pr_number));
}

/** Analyses (one per commit) per local day for the last `days` days, split by label. */
export function perDay(items: Assessment[], days = 7, now = new Date()) {
  const out = Array.from({ length: days }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (days - 1 - i));
    return { key: d.toDateString(), day: d.toLocaleDateString(undefined, { weekday: 'short' }),
             full: d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' }),
             High: 0, Medium: 0, Low: 0, none: 0 };
  });
  for (const row of items) {
    if (!row.created_at) continue;
    const slot = out.find(d => d.key === new Date(row.created_at as string).toDateString());
    if (slot) slot[row.risk_label ?? 'none'] += 1;
  }
  return out;
}

// Kinds of issue, read from the rule factors the agent saved (agents/risk_rules.py wording)
const ISSUES: [string, RegExp][] = [
  ['Sensitive area', /^sensitive area: (high|medium)/],
  ['Defect history', /^defect history: \d+ past fix/],
  ['Large change', /^size: .*\(([5-9]|\d\d) pts\)/],
  ['New module', /^new module:/],
  ['Removed check', /^removal:/],
  ['Secret in code', /^(secret in code|possible secret):/],
  ['CI failing', /^ci: failing/],
  ['Risk question', /^question \w+: yes/],
  ['Incomplete read', /^incomplete:/],
];

/** How many pull requests show each kind of issue, split by that pull request's label. */
export function issueTypes(latest: Assessment[]) {
  return ISSUES.map(([name, re]) => {
    const row = { name, High: 0, Medium: 0, Low: 0 };
    for (const pr of latest) if (pr.risk_label && pr.risk_factors.some(f => re.test(f))) row[pr.risk_label] += 1;
    return row;
  }).filter(r => r.High + r.Medium + r.Low > 0);
}

function Donut({ parts, unit, label }: { parts: { name: string; value: number; color: string; risk?: RiskLabel }[]; unit: string; label: string }) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  const r = 54, C = 2 * Math.PI * r, gap = total > 1 ? 2.5 : 0;
  let off = 0;
  return (
    <div className="donut-wrap">
      <svg width="140" height="140" viewBox="0 0 140 140" role="img"
           aria-label={`${label}: ${parts.map(p => `${p.value} ${p.name}`).join(', ')}`}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--soft)" strokeWidth="16" />
        {total > 0 && parts.map(p => {
          const len = (p.value / total) * C;
          const el = p.value ? (
            <circle key={p.name} cx="70" cy="70" r={r} fill="none" stroke={p.color} strokeWidth="16"
                    strokeDasharray={`${Math.max(len - gap, 0)} ${C}`} strokeDashoffset={-off} transform="rotate(-90 70 70)">
              <title>{`${p.name}: ${p.value} ${unit}`}</title>
            </circle>
          ) : null;
          off += len;
          return el;
        })}
        <text x="70" y="68" textAnchor="middle" className="donut-n">{total}</text>
        <text x="70" y="88" textAnchor="middle" className="donut-u">{unit}</text>
      </svg>
      <ul className="clegend">
        {parts.map(p => (
          <li key={p.name}>
            {p.risk ? <Glyph label={p.risk} /> : <i className="rdot" style={{ background: p.color }} aria-hidden="true"></i>}
            <span>{p.name}</span><b>{p.value}</b><em>{total ? Math.round((p.value / total) * 100) : 0}%</em>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Day = ReturnType<typeof perDay>[number];
const OPEN_MS = 320;  // matches the expand / collapse animation in risk.css

/** T-097: Analyses per day as its own full-width section: grouped bars per day (High, Medium, Low, not scored) on a
 * scale with gridlines, and View as table expanding the section into the full table under a smaller chart. */
function PerDay({ days }: { days: Day[] }) {
  const [table, setTable] = useState<'closed' | 'open' | 'closing'>('closed');
  const [tip, setTip] = useState<number | null>(null);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const toggle = () => {
    window.clearTimeout(timer.current);
    if (table === 'open') {  // play the collapse, then take the table out
      setTable('closing');
      timer.current = window.setTimeout(() => setTable('closed'), matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : OPEN_MS);
    } else setTable('open');
  };
  const max = Math.ceil(Math.max(3, ...days.flatMap(d => [d.High, d.Medium, d.Low, d.none])) / 3) * 3;  // even, whole ticks
  const ticks = [max, max * 2 / 3, max / 3, 0];
  const total = (d: Day) => d.High + d.Medium + d.Low + d.none;
  const sum = (k: 'High' | 'Medium' | 'Low' | 'none') => days.reduce((n, d) => n + d[k], 0);
  const all = days.reduce((n, d) => n + total(d), 0);
  const open = table !== 'closed';

  return (
    <section className={'rchart rday' + (table === 'open' ? ' expanded' : '')} aria-label="Analyses per day">
      <header>
        <div>
          <h2>Analyses per day</h2>
          <span>one per analysed commit, last {days.length} days · {all} in all</span>
        </div>
        <div className="rday-tools">
          <div className="clegend row">
            {RISKS.map(k => <span key={k}><Glyph label={k} />{k}</span>)}
            <span><i className="rdot none" aria-hidden="true"></i>Not scored</span>
          </div>
          <button className="btn ghost sm" onClick={toggle} aria-expanded={table === 'open'} aria-controls={open ? 'rday-table' : undefined}>
            {table === 'open' ? 'View as chart' : 'View as table'}
          </button>
        </div>
      </header>

      <div className="rday-plot">
        <div className="rday-axis" aria-hidden="true">{ticks.map((t, i) => <span key={i}>{t}</span>)}</div>
        <div className="rbars" onMouseLeave={() => setTip(null)}>
          <span className="rday-gridlines" aria-hidden="true">
            {ticks.map((_, i) => <i key={i} className={'rday-grid' + (i === ticks.length - 1 ? ' base' : '')}
                                    style={{ bottom: `${(1 - i / (ticks.length - 1)) * 100}%` }}></i>)}
          </span>
          {days.map((d, i) => (
            <button key={d.key} className="rbar" onMouseEnter={() => setTip(i)} onFocus={() => setTip(i)} onBlur={() => setTip(null)}
                    aria-label={`${d.full}: ${d.High} High, ${d.Medium} Medium, ${d.Low} Low, ${d.none} not scored`}>
              <span className="rbar-group">
                {(['High', 'Medium', 'Low', 'none'] as const).map(k => (
                  <span key={k} className={'rbar-col ' + k.toLowerCase() + (d[k] ? '' : ' zero')}
                        style={{ height: `${(d[k] / max) * 100}%`, ...(k === 'none' ? {} : { '--c': FILL[k] }) } as CSSProperties}></span>
                ))}
              </span>
              <span className="rbar-x">{d.day}</span>
              {tip === i && (
                <span className="rtip" role="tooltip">
                  <b>{d.full}</b>
                  {RISKS.map(k => <span key={k}><Glyph label={k} />{k}<em>{d[k]}</em></span>)}
                  {d.none > 0 && <span>Not scored<em>{d.none}</em></span>}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {open && (
        <div id="rday-table" className={'rday-more' + (table === 'closing' ? ' closing' : '')}>
          <div className="rday-more-in">
            <div className="tablewrap"><table className="grid rday-table">
              <thead><tr><th>Day</th><th className="num">High</th><th className="num">Medium</th><th className="num">Low</th>
                <th className="num">Not scored</th><th className="num">Total</th></tr></thead>
              <tbody>{days.map(d => (
                <tr key={d.key}><td>{d.full}</td><td className="num">{d.High}</td><td className="num">{d.Medium}</td><td className="num">{d.Low}</td>
                  <td className="num">{d.none}</td><td className="num"><b>{total(d)}</b></td></tr>
              ))}</tbody>
              <tfoot><tr><td>All {days.length} days</td><td className="num">{sum('High')}</td><td className="num">{sum('Medium')}</td>
                <td className="num">{sum('Low')}</td><td className="num">{sum('none')}</td><td className="num"><b>{all}</b></td></tr></tfoot>
            </table></div>
          </div>
        </div>
      )}
    </section>
  );
}

export function RiskCharts({ items, counts }: { items: Assessment[]; counts: RiskFeed['counts'] }) {
  const latest = latestPerPr(items);
  const issues = issueTypes(latest);
  const imax = Math.max(1, ...issues.map(i => i.High + i.Medium + i.Low));

  return (
    <div className="rcharts-all" aria-label="Risk charts">
      <div className="rcharts">
        <section className="rchart">
          <header><h2>Risk distribution</h2><span>latest result per PR</span></header>
          <Donut label="Risk distribution" unit="pull requests"
                 parts={RISKS.map(k => ({ name: k, value: counts[k] ?? 0, color: FILL[k], risk: k }))} />
        </section>

        <section className="rchart">
          <header><h2>Analysis status</h2><span>where each PR stands</span></header>
          <Donut label="Analysis status" unit="pull requests"
                 parts={[{ name: 'Scored', value: counts.scored ?? 0, color: '#31c47f' },  // all from the API's counts
                         { name: 'Needs review', value: counts.needs_review ?? 0, color: '#fab219' },
                         { name: 'Running', value: counts.pending ?? 0, color: 'hsl(var(--accent))' },
                         { name: 'Failed', value: counts.failed ?? 0, color: '#d03b3b' }]} />
        </section>

        <section className="rchart wide">
          <header><h2>Issues by type</h2><span>PRs showing each issue, split by their label</span></header>
          {issues.length ? (
            <div className="rissues">
              {issues.map(row => (
                <div key={row.name} className="rissue" title={`${row.name}: ${row.High} High, ${row.Medium} Medium, ${row.Low} Low`}>
                  <span>{row.name}</span>
                  <span className="rissue-track">
                    {RISKS.map(k => row[k] ? <span key={k} style={{ width: `${(row[k] / imax) * 100}%`, background: FILL[k] }}></span> : null)}
                  </span>
                  <b>{row.High + row.Medium + row.Low}</b>
                </div>
              ))}
            </div>
          ) : <p className="muted">No issues recorded in the latest results yet.</p>}
          {issues.length > 0 && <div className="clegend row">{RISKS.map(k => <span key={k}><Glyph label={k} />{k} PRs</span>)}</div>}
        </section>
      </div>

      <PerDay days={perDay(items)} />
    </div>
  );
}

/** Every analysis of one pull request, newest first: how its risk moved from commit to commit. */
export function History({ rows }: { rows: Assessment[] }) {
  if (rows.length < 2) return null;
  return (
    <div>
      <h4>Analysis history · one per commit</h4>
      <ol className="rhist">
        {rows.map(r => (
          <li key={r.id}>
            <code>{r.head_sha.slice(0, 7)}</code>
            {r.risk_label ? <span className="rhist-l"><Glyph label={r.risk_label} />{r.risk_label}{r.score !== null ? ` · ${r.score}` : ''}</span>
                          : <span className="muted">not scored</span>}
            <span className="muted">{r.state.replace(/_/g, ' ')}</span>
            {r.created_at && <time dateTime={r.created_at}>{new Date(r.created_at).toLocaleString()}</time>}
          </li>
        ))}
      </ol>
    </div>
  );
}
