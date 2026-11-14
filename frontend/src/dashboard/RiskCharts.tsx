/* Charts for Risk Analysis (T-036, prompt §8 A). Every value comes from /api/analysis/pull-requests, nothing is
 * invented. Design follows the approved prototype: risk shapes (triangle, diamond, circle) plus words, never colour
 * alone; each chart has a legend, hover/focus details, and the per-day chart can be read as a table.
 */
import { useState } from 'react';
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

export function RiskCharts({ items, counts }: { items: Assessment[]; counts: RiskFeed['counts'] }) {
  const [asTable, setAsTable] = useState(false);
  const [tip, setTip] = useState<number | null>(null);
  const latest = latestPerPr(items);
  const days = perDay(items);
  const max = Math.max(3, ...days.map(d => d.High + d.Medium + d.Low + d.none));
  const issues = issueTypes(latest);
  const imax = Math.max(1, ...issues.map(i => i.High + i.Medium + i.Low));

  return (
    <div className="rcharts" aria-label="Risk charts">
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
        <header>
          <h2>Analyses per day</h2>
          <button className="btn ghost sm" onClick={() => setAsTable(!asTable)} aria-pressed={asTable}>
            {asTable ? 'View as chart' : 'View as table'}
          </button>
        </header>
        {asTable ? (
          <div className="tablewrap"><table className="grid">
            <thead><tr><th>Day</th><th className="num">High</th><th className="num">Medium</th><th className="num">Low</th><th className="num">Not scored</th></tr></thead>
            <tbody>{days.map(d => (
              <tr key={d.key}><td>{d.full}</td><td className="num">{d.High}</td><td className="num">{d.Medium}</td><td className="num">{d.Low}</td><td className="num">{d.none}</td></tr>
            ))}</tbody>
          </table></div>
        ) : (
          <div className="rbars" onMouseLeave={() => setTip(null)}>
            {days.map((d, i) => {
              const total = d.High + d.Medium + d.Low + d.none;
              return (
                <button key={d.key} className="rbar" onMouseEnter={() => setTip(i)} onFocus={() => setTip(i)} onBlur={() => setTip(null)}
                        aria-label={`${d.full}: ${d.High} High, ${d.Medium} Medium, ${d.Low} Low, ${d.none} not scored`}>
                  <span className="rbar-stack" style={{ height: `${(total / max) * 100}%` }}>
                    {(['none', 'Low', 'Medium', 'High'] as const).map(k => d[k] ? (
                      <span key={k} style={{ flex: d[k], background: k === 'none' ? 'var(--hair)' : FILL[k] }}></span>
                    ) : null)}
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
              );
            })}
          </div>
        )}
        <div className="clegend row">{RISKS.map(k => <span key={k}><Glyph label={k} />{k}</span>)}</div>
      </section>

      <section className="rchart wide2">
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
