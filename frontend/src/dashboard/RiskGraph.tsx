/* T-038 Dependency graph (prompt §8 B), the approved prototype's black canvas on real data.
 * Files come from GET /api/analysis/pull-requests/{id}/files, read from GitHub when a PR is picked. Columns are
 * folders, ordered so an importing folder sits left of the folder it imports; arrows point at the imported file.
 * The file list beside the graph holds the same data, for keyboard and screen reader use.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { keep, peek } from './cache';
import { ApiError, api, type Assessment, type PrFile, type PrFiles, type RiskLabel } from './api';
import { Glyph, RISKS, latestPerPr } from './RiskCharts';
import './risk-views.css';

const NW = 196, NH = 58, COL = 268, ROW = 72, GAP = 30, PRX = 24, PRW = 212, PRH = 104, X0 = 300, Y0 = 40;
const base = (p: string) => p.split('/').pop() || p;
const dir = (p: string) => p.slice(0, p.lastIndexOf('/') + 1);
const ext = (p: string) => (p.includes('.') ? p.split('.').pop()!.slice(0, 4).toUpperCase() : 'FILE');
const curve = (x1: number, y1: number, x2: number, y2: number) => {
  const dx = Math.max(40, (x2 - x1) * 0.5);
  return `M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`;
};

/** Positions: one column per folder, importers left of what they import (cycles stop after one pass per folder). */
export function layout(files: PrFile[], edges: [string, string][]) {
  const folders = [...new Set(files.map(f => f.folder))].sort();
  const folderOf = new Map(files.map(f => [f.path, f.folder]));
  const col = new Map(folders.map(f => [f, 0]));
  for (let i = 0; i < folders.length; i++) {
    for (const [a, b] of edges) {
      const fa = folderOf.get(a)!, fb = folderOf.get(b)!;
      if (fa !== fb && col.get(fb)! < col.get(fa)! + 1) col.set(fb, Math.min(col.get(fa)! + 1, folders.length));
    }
  }
  const pos = new Map<string, { x: number; y: number }>();
  const lanes: { folder: string; x: number; y: number }[] = [];
  const cols = [...new Set(col.values())].sort((a, b) => a - b);
  let height = 0;
  cols.forEach((c, ci) => {
    let y = Y0;
    for (const folder of folders.filter(f => col.get(f) === c)) {
      lanes.push({ folder, x: X0 + ci * COL, y });
      y += 22;
      for (const f of files.filter(f => f.folder === folder)) { pos.set(f.path, { x: X0 + ci * COL, y }); y += ROW; }
      y += GAP;
    }
    height = Math.max(height, y);
  });
  return { pos, lanes, width: X0 + cols.length * COL + 40, height: Math.max(height, PRH + 2 * Y0) };
}

export default function RiskGraph({ items, pick: initial, active }: { items: Assessment[]; pick: number | null; active: boolean }) {
  const prs = useMemo(() => latestPerPr(items), [items]);
  const [id, setId] = useState<number | null>(initial ?? prs[0]?.id ?? null);
  const [data, setData] = useState<PrFiles | null>(null);
  const [error, setError] = useState('');
  const [attempt, setTry] = useState(0);
  const [q, setQ] = useState('');
  const [sel, setSel] = useState<string | null>(null);
  const [show, setShow] = useState({ imp: true, con: true, hideLow: false });
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const vp = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; ox: number; oy: number; moved: boolean } | null>(null);
  const row = prs.find(p => p.id === id) ?? null;

  useEffect(() => { if (initial) setId(initial); }, [initial]);
  // T-096: the view is mounted before the feed arrives, so pick the newest pull request once there is one
  useEffect(() => { if (id === null && prs.length) setId(prs[0].id); }, [id, prs]);
  // T-096: read only once the graph is shown, and once per analysis. An analysis is one commit, so its files never
  // change: the tab's cache answers every later open, switch or reload (Try again reads it again).
  const shown = useRef('');
  useEffect(() => {
    if (!id || !active || shown.current === `${id}:${attempt}`) return;
    shown.current = `${id}:${attempt}`;
    setSel(null); setQ(''); setError('');
    const hit = attempt === 0 ? peek<PrFiles>(`files:${id}`) : undefined;
    if (hit) { setData(hit); return; }
    let live = true;
    setData(null);
    api.prFiles(id).then(d => live && setData(keep(`files:${id}`, d)))
      .catch(e => live && setError(e instanceof ApiError ? e.message : 'Could not load the changed files'));
    return () => { live = false; };
  }, [id, attempt, active]);

  const g = useMemo(() => data && layout(data.files, data.edges), [data]);
  const fit = () => {
    const el = vp.current;
    if (!el || !g) return;
    const k = Math.max(0.35, Math.min((el.clientWidth - 64) / g.width, (el.clientHeight - 104) / g.height, 1.15));
    setView({ k, x: (el.clientWidth - g.width * k) / 2, y: (el.clientHeight - g.height * k) / 2 + 18 });
  };
  useEffect(() => { if (active) fit(); }, [g, active]);  // a hidden view has no size to fit to
  const zoomAt = (k: number, mx: number, my: number) => setView(v => {
    const nk = Math.min(Math.max(k, 0.35), 2.2);
    return { k: nk, x: mx - (mx - v.x) * (nk / v.k), y: my - (my - v.y) * (nk / v.k) };
  });
  useEffect(() => {  // wheel needs a non-passive listener to stop the page scrolling
    const el = vp.current;
    if (!el) return;
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      setView(v => {
        const nk = Math.min(Math.max(v.k * Math.exp(-e.deltaY * 0.0015), 0.35), 2.2), mx = e.clientX - r.left, my = e.clientY - r.top;
        return { k: nk, x: mx - (mx - v.x) * (nk / v.k), y: my - (my - v.y) * (nk / v.k) };
      });
    };
    el.addEventListener('wheel', wheel, { passive: false });
    return () => el.removeEventListener('wheel', wheel);
  }, [data]);

  if (!prs.length) return <div className="empty"><b>No pull requests analysed yet</b>The graph shows the files of an analysed pull request.</div>;

  const files = data?.files ?? [];
  const visible = files.filter(f => !(show.hideLow && f.risk === 'Low'));
  const ids = new Set(visible.map(f => f.path));
  const edges = (data?.edges ?? []).filter(([a, b]) => ids.has(a) && ids.has(b));
  const near = new Set([sel]);
  edges.forEach(([a, b]) => { if (a === sel) near.add(b); if (b === sel) near.add(a); });
  const query = q.trim().toLowerCase();
  const focus = (p: string) => (query ? p.toLowerCase().includes(query) : !sel || near.has(p));
  const picked = files.find(f => f.path === sel) ?? null;
  const count = (k: RiskLabel) => files.filter(f => f.risk === k).length;
  const center = (p: string) => {
    const el = vp.current, at = g?.pos.get(p);
    if (el && at) setView(v => ({ ...v, x: el.clientWidth / 2 - (at.x + NW / 2) * v.k, y: el.clientHeight / 2 - (at.y + NH / 2) * v.k }));
  };
  const toggle = (key: keyof typeof show, label: string) => (
    <button aria-pressed={show[key]} onClick={() => setShow(s => ({ ...s, [key]: !s[key] }))}>{label}</button>
  );

  return (
    <div className="rgraph">
      <div className="rg-head">
        <p className="muted">
          {data ? <>PR #{row?.pr_number} · {data.shown_files} changed file{data.shown_files === 1 ? '' : 's'} in {g?.lanes.length} folder{g?.lanes.length === 1 ? '' : 's'} · {data.edges.length} import{data.edges.length === 1 ? '' : 's'} between them · arrows point at the file being imported</>
                : error ? 'The changed files could not be read' : 'Reading the changed files from GitHub'}
        </p>
        <div className="rg-tools">
          <select className="rg-select" aria-label="Pull request" value={id ?? ''} onChange={e => setId(Number(e.target.value))}>
            {prs.map(p => <option key={p.id} value={p.id}>#{p.pr_number} · {p.title || 'Untitled'}</option>)}
          </select>
          <input className="rg-find" type="search" placeholder="Find a file" aria-label="Find a file" value={q}
                 onChange={e => { setQ(e.target.value); setSel(null); }} />
          <div className="seg" role="group" aria-label="View options">
            {toggle('imp', 'Imports')}{toggle('con', 'PR links')}{toggle('hideLow', 'Hide Low')}
          </div>
        </div>
      </div>

      {data && !data.same_commit && (
        <div className="warnbox">The pull request has newer commits than the analysed one ({row?.head_sha.slice(0, 7)}). The files shown are from {data.head_sha.slice(0, 7)}.</div>
      )}
      {data && data.total_files > data.shown_files && (
        <div className="warnbox">Showing the first {data.shown_files} of {data.total_files} changed files.</div>
      )}

      <div className={'vp' + (drag.current ? ' drag' : '')} ref={vp} aria-label={`Dependency graph of PR ${row?.pr_number ?? ''}. The same data is in the file list below.`}
           onPointerDown={e => {
             if ((e.target as HTMLElement).closest('.node,.overlay')) return;
             drag.current = { x: e.clientX, y: e.clientY, ox: view.x, oy: view.y, moved: false };
             e.currentTarget.setPointerCapture(e.pointerId);
           }}
           onPointerMove={e => {
             const d = drag.current;
             if (!d) return;
             const dx = e.clientX - d.x, dy = e.clientY - d.y;
             if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
             setView(v => ({ ...v, x: d.ox + dx, y: d.oy + dy }));
           }}
           onPointerUp={() => { if (drag.current && !drag.current.moved) setSel(null); drag.current = null; }}
           style={{ backgroundSize: `${22 * view.k}px ${22 * view.k}px`, backgroundPosition: `${view.x}px ${view.y}px` }}>
        {!data && (
          <div className="overlay gstate" role={error ? 'alert' : 'status'}>
            {error ? <><b>Could not draw the graph</b><span>{error}</span><button className="btn ghost sm" onClick={() => setTry(t => t + 1)}>Try again</button></>
                   : <><span className="spin" aria-hidden="true"></span><span>Reading the changed files from GitHub</span></>}
          </div>
        )}
        {data && g && (
          <div className="world" style={{ width: g.width, height: g.height, transform: `translate(${view.x}px,${view.y}px) scale(${view.k})` }}>
            <svg className="edges" width={g.width} height={g.height} aria-hidden="true">
              <defs>
                <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="rgba(122,102,234,.8)" /></marker>
                <marker id="arh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#B9AFFF" /></marker>
              </defs>
              {show.con && visible.map(f => {
                const p = g.pos.get(f.path)!, prY = Y0 + 20;
                return <path key={'c' + f.path} className={'e-contain' + (query && !focus(f.path) ? ' dim' : '')} d={curve(PRX + PRW, prY + PRH / 2, p.x, p.y + NH / 2)} />;
              })}
              {show.imp && edges.map(([a, b]) => {
                const pa = g.pos.get(a)!, pb = g.pos.get(b)!, hi = !query && (a === sel || b === sel);
                const dim = query ? !(focus(a) || focus(b)) : !!sel && !hi;
                const back = pb.x <= pa.x;  // same folder or a cycle: loop round instead of crossing the node
                const d = back ? `M${pa.x + NW} ${pa.y + NH / 2} C${pa.x + NW + 60} ${pa.y + NH / 2} ${pb.x + NW + 60} ${pb.y + NH / 2} ${pb.x + NW + 2} ${pb.y + NH / 2}`
                               : curve(pa.x + NW, pa.y + NH / 2, pb.x - 2, pb.y + NH / 2);
                return <path key={a + '>' + b} className={'e-imp' + (hi ? ' hi' : '') + (dim ? ' dim' : '')} markerEnd={`url(#${hi ? 'arh' : 'ar'})`} d={d} />;
              })}
            </svg>
            {g.lanes.map(l => <div key={l.folder} className="lane" style={{ left: l.x, top: l.y }}>{l.folder}</div>)}
            <div className="prnode" style={{ left: PRX, top: Y0 + 20 }}>
              <span className="m">PR #{row?.pr_number} · {row?.head_sha.slice(0, 7)}</span>
              <span className="t">{row?.title || 'Untitled pull request'}</span>
              <span className="prnode-tags">
                {row?.risk_label && <span className="gbadge"><Glyph label={row.risk_label} />{row.risk_label}{row.score !== null ? ` · ${row.score}` : ''}</span>}
                <span className="gbadge mono">{files.length} files</span>
              </span>
              <span className="port out"></span>
            </div>
            {visible.map(f => {
              const p = g.pos.get(f.path)!, on = f.path === sel, dim = !focus(f.path);
              return (
                <button key={f.path} className={'node' + (on ? ' sel' : '') + (dim ? ' dim' : '') + (query && !dim ? ' match' : '')}
                        style={{ left: p.x, top: p.y }} aria-pressed={on} aria-label={`${base(f.path)}, ${f.risk} risk`}
                        onClick={e => { e.stopPropagation(); setSel(on ? null : f.path); setQ(''); }}>
                  <span className="port in"></span>
                  <span className="ext">{ext(f.path)}</span>
                  <span className="nm"><b>{base(f.path)}</b><span>{dir(f.path) || '/'}</span></span>
                  <Glyph label={f.risk} />
                  <span className="port out"></span>
                </button>
              );
            })}
          </div>
        )}
        <div className="overlay legend-o">
          {RISKS.map(k => <span key={k}><Glyph label={k} />{k}</span>)}
          <span><svg width="26" height="8" aria-hidden="true"><path d="M0 4h20" stroke="#7A66EA" strokeWidth="1.5" /><path d="M18 1l6 3-6 3z" fill="#7A66EA" /></svg>imports</span>
          <span><svg width="26" height="8" aria-hidden="true"><path d="M0 4h26" stroke="rgba(255,255,255,.25)" /></svg>changed in PR</span>
        </div>
        <div className="overlay zoom">{Math.round(view.k * 100)}%</div>
        <div className="overlay ctrls">
          <button aria-label="Zoom in" onClick={() => zoomAt(view.k * 1.2, (vp.current?.clientWidth ?? 0) / 2, (vp.current?.clientHeight ?? 0) / 2)}>+</button>
          <button aria-label="Zoom out" onClick={() => zoomAt(view.k / 1.2, (vp.current?.clientWidth ?? 0) / 2, (vp.current?.clientHeight ?? 0) / 2)}>−</button>
          <button aria-label="Fit to screen" onClick={fit}>⤢</button>
        </div>
      </div>

      {data && (
        <div className="inspect">
          <section className="rchart" aria-label="File details">
            {picked ? (
              <>
                <header><div className="ins-title"><span className="mono">{picked.path}</span><h2>{base(picked.path)}</h2></div>
                  <span className="gbadge"><Glyph label={picked.risk} />{picked.risk}</span></header>
                <div className="kv">
                  <div><span>Added</span><b className="add">+{picked.additions}</b></div>
                  <div><span>Removed</span><b className="del">−{picked.deletions}</b></div>
                  <div><span>Status</span><b className="plain">{picked.status}</b></div>
                </div>
                <div><h4>Why</h4><p>{picked.why}.</p></div>
                <div className="ins-two">
                  <div><h4>Imports</h4><span className="mono muted">{data.edges.filter(e => e[0] === picked.path).map(e => base(e[1])).join(', ') || 'none'}</span></div>
                  <div><h4>Imported by</h4><span className="mono muted">{data.edges.filter(e => e[1] === picked.path).map(e => base(e[0])).join(', ') || 'none'}</span></div>
                </div>
              </>
            ) : (
              <>
                <header><h2>Files by risk</h2><span>PR #{row?.pr_number}</span></header>
                <div className="kv">{RISKS.map(k => <div key={k}><span><Glyph label={k} /> {k}</span><b>{count(k)}</b></div>)}</div>
                <p className="muted">
                  Select a file in the graph or the list to see why it was flagged and what it imports. Drag to pan, scroll to zoom,
                  click empty space to clear. Imports were looked for in {data.scanned_for_imports} code file{data.scanned_for_imports === 1 ? '' : 's'}.
                </p>
              </>
            )}
          </section>
          <section className="rchart" aria-label="Changed files">
            <header><h2>Changed files</h2><span>same data as the graph</span></header>
            <div className="flist">
              {files.map(f => (
                <button key={f.path} aria-pressed={f.path === sel} onClick={() => { setSel(f.path); setQ(''); center(f.path); }}>
                  <Glyph label={f.risk} /><span className="flist-p">{f.path}</span><span>{f.risk}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
