/* Charts for Risk Analysis (T-036, prompt §8 A). Every value comes from /api/analysis/pull-requests, nothing is
 * invented. Design follows the approved prototype: risk shapes (triangle, diamond, circle) plus words, never colour
 * alone; each chart has a legend, hover/focus details, and the per-day chart can be read as a table.
 */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
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

const pctOf = (v: number, total: number) => (total ? Math.round((v / total) * 100) : 0);

/** T-089: hover, focus or touch a slice or its legend row to read it: it grows, the others fade, the centre shows it. */
function Donut({ parts, unit, label }: { parts: Part[]; unit: string; label: string }) {
  const [on, setOn] = useState<number | null>(null);
  const total = parts.reduce((s, p) => s + p.value, 0);
  const r = 54, C = 2 * Math.PI * r, gap = total > 1 ? 2.5 : 0;
  const pick = on !== null ? parts[on] : null;
  let off = 0;
  return (
    <div className={'donut-wrap' + (on !== null ? ' focus' : '')} onMouseLeave={() => setOn(null)}>
      <svg width="140" height="140" viewBox="0 0 140 140" role="img"
           aria-label={`${label}: ${parts.map(p => `${p.value} ${p.name}`).join(', ')}`}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--soft)" strokeWidth="16" />
        {total > 0 && parts.map((p, i) => {
          const len = (p.value / total) * C;
          // the picked slice slides out along its own middle, like a slice lifted from the pie (not when it is the only one)
          const mid = ((off + len / 2) / C) * 2 * Math.PI - Math.PI / 2;
          const lift = on === i && parts.filter(x => x.value).length > 1 ? 7 : 0;
          const el = p.value ? (
            <circle key={p.name} className={'dseg' + (on === i ? ' on' : on !== null ? ' dim' : '')} cx="70" cy="70" r={r} fill="none"
                    stroke={p.color} strokeWidth="16" strokeDasharray={`${Math.max(len - gap, 0)} ${C}`} strokeDashoffset={-off}
                    style={{ transform: `translate(${Math.cos(mid) * lift}px, ${Math.sin(mid) * lift}px) rotate(-90deg)` }}
                    onMouseEnter={() => setOn(i)} onClick={() => setOn(on === i ? null : i)} />
          ) : null;
          off += len;
          return el;
        })}
        {pick ? (
          // a picked slice: its count and its share; its name lights up in the legend beside, so it is never cut short
          <g key={'p' + on} className="dswap">
            <text x="70" y="68" textAnchor="middle" className="donut-n">{pick.value}</text>
            <text x="70" y="88" textAnchor="middle" className="donut-u donut-pct">{pctOf(pick.value, total)}% of {total}</text>
          </g>
        ) : (
          <g key="all" className="dswap">
            <text x="70" y="68" textAnchor="middle" className="donut-n">{total}</text>
            <text x="70" y="88" textAnchor="middle" className="donut-u">{unit}</text>
          </g>
        )}
      </svg>
      <ul className="clegend">
        {parts.map((p, i) => (
          <li key={p.name} className={on === i ? 'on' : on !== null ? 'dim' : ''} tabIndex={0}
              onMouseEnter={() => setOn(i)} onFocus={() => setOn(i)} onBlur={() => setOn(null)}>
            {p.risk ? <Glyph label={p.risk} /> : <i className="rdot" style={{ background: p.color }} aria-hidden="true"></i>}
            <span>{p.name}</span><b>{p.value}</b><em>{pctOf(p.value, total)}%</em>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Part = { name: string; value: number; color: string; risk?: RiskLabel };

/** T-089: the same parts as horizontal bars. Hover, focus or touch a row: it lights up, the others fade, a tip reads it. */
function PartBars({ parts, unit, label }: { parts: Part[]; unit: string; label: string }) {
  const [on, setOn] = useState<number | null>(null);
  const total = parts.reduce((s, p) => s + p.value, 0);
  const max = Math.max(1, ...parts.map(p => p.value));
  return (
    <ul className={'pbars' + (on !== null ? ' focus' : '')} aria-label={`${label}: ${parts.map(p => `${p.value} ${p.name}`).join(', ')}`}
        onMouseLeave={() => setOn(null)}>
      {parts.map((p, i) => (
        <li key={p.name} className={on === i ? 'on' : on !== null ? 'dim' : ''} tabIndex={0}
            onMouseEnter={() => setOn(i)} onFocus={() => setOn(i)} onBlur={() => setOn(null)} onClick={() => setOn(on === i ? null : i)}>
          <span className="pbars-n">{p.risk ? <Glyph label={p.risk} /> : <i className="rdot" style={{ background: p.color }} aria-hidden="true"></i>}{p.name}</span>
          <span className="pbars-track">
            <i style={{ width: `${(p.value / max) * 100}%`, background: p.color, animationDelay: `${i * 70}ms` }}></i>
            {on === i && (
              <span className="pbars-tip" role="status" style={{ left: `${Math.max(6, (p.value / max) * 100)}%` }}>
                <b>{p.name}</b><span>{p.value} {unit} · {pctOf(p.value, total)}%</span>
              </span>
            )}
          </span>
          <b>{p.value}</b><em>{pctOf(p.value, total)}%</em>
        </li>
      ))}
    </ul>
  );
}

type Kind = 'pie' | 'bar';
/** Pie or bar, picked by the viewer and remembered in this browser only (a convenience, never needed to read the page). */
function useKind(key: string, start: Kind): [Kind, (k: Kind) => void] {
  const [kind, setKind] = useState<Kind>(() => {
    try { const v = localStorage.getItem('verixa.chart.' + key); return v === 'pie' || v === 'bar' ? v : start; } catch { return start; }
  });
  return [kind, (k: Kind) => { setKind(k); try { localStorage.setItem('verixa.chart.' + key, k); } catch { /* storage blocked: the choice lasts this visit */ } }];
}

function KindSwitch({ kind, set, label }: { kind: Kind; set: (k: Kind) => void; label: string }) {
  return (
    <div className="seg ckind" role="group" aria-label={`${label}: chart type`}>
      <button aria-pressed={kind === 'pie'} onClick={() => set('pie')}>Pie</button>
      <button aria-pressed={kind === 'bar'} onClick={() => set('bar')}>Bar</button>
    </div>
  );
}

/** A chart of parts the viewer can show as a pie (donut) or as bars. */
function PartsChart({ id, title, sub, parts, unit, start = 'pie' }: { id: string; title: string; sub: string; parts: Part[]; unit: string; start?: Kind }) {
  const [kind, setKind] = useKind(id, start);
  return (
    <>
      <header><div className="chead"><h2>{title}</h2><span>{sub}</span></div><KindSwitch kind={kind} set={setKind} label={title} /></header>
      <div key={kind} className="ckind-body">
        {kind === 'pie' ? <Donut label={title} unit={unit} parts={parts} /> : <PartBars label={title} unit={unit} parts={parts} />}
      </div>
    </>
  );
}

const ISSUE_COLORS = ['#7A66EA', '#2EC2B3', '#fab219', '#d03b3b', '#5FA8F5', '#E07BC6', '#31c47f', '#B9AFFF', '#9CA3AF'];

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

export function RiskCharts({ items, counts, trend }: { items: Assessment[]; counts: RiskFeed['counts']; trend?: ReactNode }) {
  const latest = latestPerPr(items);
  const issues = issueTypes(latest);
  const imax = Math.max(1, ...issues.map(i => i.High + i.Medium + i.Low));
  const [issueKind, setIssueKind] = useKind('issues', 'bar');

  return (
    <div className="rcharts-all" aria-label="Risk charts">
      <div className="rcharts">
        <section className="rchart">
          <PartsChart id="risk" title="Risk distribution" sub="latest result per PR" unit="pull requests"
                      parts={RISKS.map(k => ({ name: k, value: counts[k] ?? 0, color: FILL[k], risk: k }))} />
        </section>

        <section className="rchart">
          <PartsChart id="status" title="Analysis status" sub="where each PR stands" unit="pull requests"
                      parts={[{ name: 'Scored', value: counts.scored ?? 0, color: '#31c47f' },  // all from the API's counts
                              { name: 'Needs review', value: counts.needs_review ?? 0, color: '#fab219' },
                              { name: 'Running', value: counts.pending ?? 0, color: 'hsl(var(--accent))' },
                              { name: 'Failed', value: counts.failed ?? 0, color: '#d03b3b' }]} />
        </section>

        <section className="rchart wide">
          <header><div className="chead"><h2>Issues by type</h2><span>PRs showing each issue, split by their label</span></div>
            {issues.length > 0 && <KindSwitch kind={issueKind} set={setIssueKind} label="Issues by type" />}</header>
          {issues.length && issueKind === 'pie' ? (
            <div key="pie" className="ckind-body">
              <Donut label="Issues by type" unit="pull requests"
                     parts={issues.map((row, i) => ({ name: row.name, value: row.High + row.Medium + row.Low, color: ISSUE_COLORS[i % ISSUE_COLORS.length] }))} />
            </div>
          ) : issues.length ? (
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
          {issues.length > 0 && issueKind === 'bar' && <div className="clegend row">{RISKS.map(k => <span key={k}><Glyph label={k} />{k} PRs</span>)}</div>}
        </section>
      </div>

      {/* T-089: the two charts over time side by side, one even row, under the three part charts */}
      <div className="rcharts-pair">
        {trend}
        <PerDay days={perDay(items)} />
      </div>
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
