/* T-089 Overview trend: analyses against flagged risk per day, as a smooth two-series area chart (the reference's
 * "Income vs expenses" layout). Every point is counted from the saved analyses in the feed, nothing is invented.
 * Hover, touch or the arrow keys move a guide over the days to compare both series.
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import type { Assessment } from './api';

const RANGES = [7, 14, 30] as const;
type Range = typeof RANGES[number];
const H = 250;                                   // plot height in px, the width follows the card
const PAD = { top: 14, right: 10, bottom: 26, left: 34 };

export interface TrendDay { key: string; label: string; full: string; analysed: number; flagged: number }

/** Analyses (one per commit) and the flagged ones (Medium or High) per local day, oldest first. */
export function trendDays(items: Assessment[], days: number, now = new Date(), shift = 0): TrendDay[] {
  const out = Array.from({ length: days }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - shift - (days - 1 - i));
    return { key: d.toDateString(), label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
             full: d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }), analysed: 0, flagged: 0 };
  });
  const at = new Map(out.map(d => [d.key, d]));
  for (const row of items) {
    if (!row.created_at) continue;
    const day = at.get(new Date(row.created_at).toDateString());
    if (!day) continue;
    day.analysed += 1;
    if (row.risk_label === 'High' || row.risk_label === 'Medium') day.flagged += 1;
  }
  return out;
}

/** A smooth line through the points that never overshoots them (monotone cubic), so a count never dips below 0. */
export function smoothPath(pts: [number, number][]): string {
  if (!pts.length) return '';
  if (pts.length === 1) return `M${pts[0][0]},${pts[0][1]}`;
  const n = pts.length;
  const m = pts.slice(0, -1).map((p, i) => (pts[i + 1][1] - p[1]) / (pts[i + 1][0] - p[0]));
  const t = pts.map((_, i) => (i === 0 ? m[0] : i === n - 1 ? m[n - 2] : m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2));
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) { t[i] = 0; t[i + 1] = 0; continue; }
    const a = t[i] / m[i], b = t[i + 1] / m[i], h = a * a + b * b;
    if (h > 9) { const s = 3 / Math.sqrt(h); t[i] = s * a * m[i]; t[i + 1] = s * b * m[i]; }
  }
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], dx = (x1 - x0) / 3;
    d += `C${x0 + dx},${y0 + t[i] * dx} ${x1 - dx},${y1 - t[i + 1] * dx} ${x1},${y1}`;
  }
  return d;
}

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const watch = new ResizeObserver(() => setW(el.clientWidth));
    watch.observe(el);
    setW(el.clientWidth);
    return () => watch.disconnect();
  }, []);
  return [ref, w] as const;
}

export default function RiskTrend({ items }: { items: Assessment[] }) {
  const [range, setRange] = useState<Range>(14);
  const [tip, setTip] = useState<number | null>(null);
  const [box, width] = useWidth();
  const days = useMemo(() => trendDays(items, range), [items, range]);
  const before = useMemo(() => trendDays(items, range, new Date(), range), [items, range]);

  const total = days.reduce((n, d) => n + d.analysed, 0);
  const flagged = days.reduce((n, d) => n + d.flagged, 0);
  const prev = before.reduce((n, d) => n + d.analysed, 0);
  const change = prev ? Math.round(((total - prev) / prev) * 100) : null;

  const top = Math.max(4, ...days.map(d => d.analysed));
  const step = Math.ceil(top / 4);
  const max = step * 4;
  const ticks = [0, 1, 2, 3, 4].map(i => i * step);
  const plotW = Math.max(width - PAD.left - PAD.right, 10), plotH = H - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (days.length > 1 ? (i / (days.length - 1)) * plotW : plotW / 2);
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
  const line = (k: 'analysed' | 'flagged') => smoothPath(days.map((d, i) => [x(i), y(d[k])]));
  const area = (k: 'analysed' | 'flagged') => `${line(k)}L${x(days.length - 1)},${y(0)}L${x(0)},${y(0)}Z`;
  const every = Math.ceil(days.length / Math.max(2, Math.floor(plotW / 70)));  // as many date labels as fit

  const pick = (e: PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - PAD.left) / plotW) * (days.length - 1));
    setTip(Math.min(days.length - 1, Math.max(0, i)));
  };
  const keys = (e: KeyboardEvent<HTMLDivElement>) => {
    const next = { ArrowRight: (tip ?? -1) + 1, ArrowLeft: (tip ?? days.length) - 1, Home: 0, End: days.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    setTip(Math.min(days.length - 1, Math.max(0, next)));
  };
  const at = tip !== null ? days[tip] : null;

  return (
    <section className="rchart rtrend" aria-label="Analyses and flagged risk">
      <header className="rtrend-head">
        <div>
          <h2>Analyses vs flagged risk</h2>
          <span>Hover the chart to compare any day.</span>
        </div>
        <div className="rtrend-tools">
          <div className="clegend row">
            <span><i className="rtrend-key a" aria-hidden="true"></i>Analyses</span>
            <span><i className="rtrend-key f" aria-hidden="true"></i>Flagged (Medium or High)</span>
          </div>
          <div className="seg" role="group" aria-label="Range">
            {RANGES.map(r => <button key={r} aria-pressed={range === r} onClick={() => { setRange(r); setTip(null); }}>{r}d</button>)}
          </div>
        </div>
      </header>

      <div className="rtrend-sum">
        <b className="rtrend-total">{total}</b>
        <span className="muted">analyses in the last {range} days · {flagged} flagged</span>
        {change !== null && (
          <span className={'rtrend-delta' + (change < 0 ? ' down' : '')}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change)}% <em>than the {range} days before</em>
          </span>
        )}
      </div>

      <div className="rtrend-plot" ref={box} tabIndex={0} onKeyDown={keys} onBlur={() => setTip(null)}
           role="img" aria-label={`Analyses per day for the last ${range} days: ${total} in all, ${flagged} flagged Medium or High`}>
        {width > 0 && (
          <svg key={range} width={width} height={H} className="rtrend-svg" onPointerMove={pick} onPointerDown={pick}
               onPointerLeave={() => setTip(null)} aria-hidden="true">
            <defs>
              <linearGradient id="rtrend-fa" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="hsl(var(--accent))" stopOpacity=".38" />
                <stop offset="1" stopColor="hsl(var(--accent))" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="rtrend-ff" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="hsl(var(--foreground))" stopOpacity=".1" />
                <stop offset="1" stopColor="hsl(var(--foreground))" stopOpacity="0" />
              </linearGradient>
            </defs>
            {ticks.map(t => <line key={t} className={'rtrend-grid' + (t === 0 ? ' base' : '')} x1={PAD.left} x2={PAD.left + plotW} y1={y(t)} y2={y(t)} />)}
            <path className="rtrend-area a" d={area('analysed')} fill="url(#rtrend-fa)" />
            <path className="rtrend-area f" d={area('flagged')} fill="url(#rtrend-ff)" />
            <path className="rtrend-line f" d={line('flagged')} pathLength={1} />
            <path className="rtrend-line a" d={line('analysed')} pathLength={1} />
            {at && (
              <g className="rtrend-guide">
                <line x1={x(tip!)} x2={x(tip!)} y1={PAD.top} y2={y(0)} />
                <circle className="a" cx={x(tip!)} cy={y(at.analysed)} r="5" />
                <circle className="f" cx={x(tip!)} cy={y(at.flagged)} r="5" />
              </g>
            )}
          </svg>
        )}
        <div className="rtrend-y" aria-hidden="true">
          {ticks.map(t => <span key={t} style={{ top: y(t) }}>{t}</span>)}
        </div>
        <div className="rtrend-x" aria-hidden="true">
          {days.map((d, i) => (i % every === 0 || i === days.length - 1) && (days.length - 1 - i >= every || i === days.length - 1)
            ? <span key={d.key} style={{ left: x(i) }}>{d.label}</span> : null)}
        </div>
        {at && (
          <div className={'rtrend-tip' + (x(tip!) > width * 0.6 ? ' left' : '')} role="status"
               style={{ left: x(tip!), top: Math.min(y(at.analysed), y(at.flagged)) }}>
            <b>{at.full}</b>
            <span><i className="rtrend-key a"></i>Analyses<em>{at.analysed}</em></span>
            <span><i className="rtrend-key f"></i>Flagged<em>{at.flagged}</em></span>
          </div>
        )}
      </div>
    </section>
  );
}
