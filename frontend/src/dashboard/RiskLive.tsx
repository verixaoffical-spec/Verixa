/* T-038 Live runs and logs (prompt §8 C/D), the approved prototype's layout on real data.
 * A run in progress comes from the live socket (RiskView passes it in); finished runs come from
 * GET /api/analysis/pull-requests/{id}/log, which reads the saved trace log. A stage is marked done only when
 * a step of that stage has arrived. Checks, risks and the decision are the saved assessment's own fields.
 */
import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { keep, peek } from './cache';
import { ApiError, api, type Assessment, type LiveEvent, type PastRun, type Stage } from './api';
import { Glyph, latestPerPr } from './RiskCharts';
import './premium.css';  // T-089, after risk-views.css (RiskGraph is imported first) so its rules refine those
import './overview.css';  // T-089, the Overview's reference layout, after premium.css
import './processing.css';  // T-089, the live processing card, white logs in the light theme; loaded last

const STAGES: [string, Stage][] = [['Received', 'received'], ['Read changes', 'changes'], ['Defect history', 'history'], ['CI', 'ci'],
  ['Rules', 'rules'], ['Model', 'model'], ['Manager', 'manager'], ['Saved', 'saved']];
const GROUPS: Record<string, Stage[] | null> = { All: null, GitHub: ['received', 'changes', 'history', 'ci'], Rules: ['rules'],
  Model: ['model'], Manager: ['manager', 'saved'] };
const STAGE_MS = 900;  // T-089: one stage after another, unhurried; matches --stagger in premium.css
const time = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString(undefined, { hour12: false }) : '');

/** T-099: what the saved analysis knows about the module's past defects. Kept apart from the stage's run status:
 * a pull request with no history is a result ("No defect history"), not a stage that is still waiting. */
function historyOf(a: Assessment): string | null {
  if (a.defect_history === 'found') return `${a.past_defects} past defect${a.past_defects === 1 ? '' : 's'}`;
  if (a.defect_history === 'none') return 'No defect history';
  if (a.defect_history === 'unknown') return 'History unknown';
  return null;  // still being analysed
}

export default function RiskLive({ items, live, pick, active }: { items: Assessment[]; live: { pr: number; messages: LiveEvent[]; done: boolean; startedAt: number }[]; pick: number | null; active: boolean }) {
  const prs = useMemo(() => latestPerPr(items), [items]);
  const [id, setId] = useState<number | null>(pick ?? prs[0]?.id ?? null);
  const [past, setPast] = useState<PastRun[] | null>(null);
  const [error, setError] = useState('');
  const [runIx, setRunIx] = useState(0);
  const [filter, setFilter] = useState('All');
  const row = prs.find(p => p.id === id) ?? null;
  const current = live.find(r => r.pr === row?.pr_number);

  useEffect(() => { if (pick) setId(pick); }, [pick]);
  // T-096: the view is mounted before the feed arrives, so pick the newest pull request once there is one
  useEffect(() => { if (id === null && prs.length) setId(prs[0].id); }, [id, prs]);
  // T-089: a run that starts on the live socket is followed once, so its stages fill in as the steps arrive.
  // Picking another pull request afterwards is kept; the same run never takes the view back.
  const followed = useRef(new Set<string>());
  useEffect(() => {
    for (const r of live) {
      const k = `${r.pr}:${r.startedAt}`;
      if (r.done || followed.current.has(k)) continue;
      const target = prs.find(p => p.pr_number === r.pr);
      if (!target) continue;  // its row comes with the next feed read, and this runs again then
      followed.current.add(k);
      setId(target.id);
      setRunIx(0);
    }
  }, [live, prs]);
  // T-096: the saved log is read when the view is first shown for this analysis, then kept. It is read again only when
  // a run of this pull request finishes, quietly, with the kept log on screen meanwhile.
  const read = useRef('');
  const [pastFor, setPastFor] = useState('');  // T-089: which read the saved log on screen answers
  useEffect(() => {
    if (!id || !active) return;
    const key = `${id}:${current?.done ? 'after-run' : ''}`;
    if (read.current === key) return;
    const first = !read.current.startsWith(`${id}:`);
    read.current = key;
    const hit = peek<PastRun[]>(`log:${id}`);
    if (first) { setError(''); setRunIx(0); setPast(hit ?? null); }
    if (hit && first && !current?.done) return;
    let on = true;
    api.prLog(id).then(d => { if (on) { setPast(keep(`log:${id}`, d.runs)); setPastFor(key); } })
      .catch(e => on && setError(e instanceof ApiError ? e.message : 'Could not read the saved log'));
    return () => { on = false; };
  }, [id, active, current?.done]);
  // T-089: a run that just finished on the socket stays on screen, at the same place, until the saved log includes it
  const justDone = !!current?.done && pastFor !== `${id}:after-run`;
  const [intro, setIntro] = useState(true);  // the stages fill in one after another when a run is first shown

  // the sequence plays again each time the tab is opened, and for each pull request or run picked
  const [opened, setOpened] = useState(0);
  useEffect(() => { if (active) setOpened(n => n + 1); }, [active]);
  const runKey = `${id}:${Math.min(runIx, Math.max((past?.length ?? 0) - 1, 0))}:${opened}`;
  useEffect(() => {
    setIntro(true);
    const t = window.setTimeout(() => setIntro(false), STAGES.length * STAGE_MS + 900);
    return () => window.clearTimeout(t);
  }, [runKey]);

  if (!prs.length) return <div className="empty"><b>No pull requests analysed yet</b>Runs and their logs show here once a pull request is analysed.</div>;

  const runs: { label: string; messages: LiveEvent[]; done: boolean; id: string | null }[] = [
    ...(current && (!current.done || justDone) ? [{ label: current.done ? 'latest run' : 'current run', messages: current.messages, done: current.done,
                                                    id: current.messages.find(m => m.run_id)?.run_id ?? null }] : []),
    ...(past ?? []).map(r => ({ label: `run ${(r.run_id ?? '').slice(0, 4) || '—'} · ${r.started ? new Date(r.started).toLocaleString() : ''}`,
                                messages: r.messages, done: true, id: r.run_id })),
  ];
  const run = runs[Math.min(runIx, runs.length - 1)] ?? null;
  const shown = run?.messages ?? [];
  const seen: Partial<Record<Stage, string>> = {};
  shown.forEach(m => { if (m.stage && !(m.stage in seen)) seen[m.stage] = m.at; });
  // T-089: a run that has any step was received. A saved run can lack its delivery step (the delivery is logged before the
  // run has an id), so Received takes the run's first step and its time instead of showing "not logged".
  if (shown.length && !seen.received) seen.received = shown[0].at;
  const last = shown[shown.length - 1];
  const now = run && !run.done ? last?.stage : null;
  const rules = !!seen.rules || ((!run || run.done) && !!row?.risk_factors.length);  // a saved result has its checks even when its log is gone
  const list = shown.filter(m => !GROUPS[filter] || GROUPS[filter]!.includes(m.stage));
  const errorsMsg = row?.errors.join(' · ');
  const history = row && (!run || run.done) ? historyOf(row) : null;  // during a run the saved row is the previous one
  // T-089: how far the run has got, for the track: the furthest stage that has a step (or is running now)
  const reach = Math.max(0, ...STAGES.map(([, key], i) => (key in seen || key === now ? i : 0)));
  // Defect history and CI count as covered only when their step found something to read: past fixes, or CI checks.
  // A step that says there was nothing (no history, no checks, the lookup failed) leaves the stage grey.
  const covered = (key: Stage) => {
    const steps = shown.filter(m => m.stage === key);
    if (key === 'history') return steps.some(m => m.event === 'github.defects_read' && !/: 0 found$/.test(m.text));
    if (key === 'ci') return steps.some(m => m.event.startsWith('ci.') ||
                                         (m.event === 'github.ci_read' && !/no checks run|still running/.test(m.text)));
    return true;
  };
  const view = STAGES.map(([name, key], i) => {
    const cls = key === now ? 'c' : key in seen ? 'd' : 'w';
    // Defect history and CI are grey when not covered: they reported nothing to read, or the run went past them
    // (or finished) without a step from them at all. Other stages keep "waiting" / "not logged".
    const skipped = cls === 'w' && (key === 'history' || key === 'ci') && !!run && shown.length > 0 && (run.done || reach > i);
    const grey = (cls === 'd' && !covered(key)) || skipped;
    // "waiting" only while a run is going; a finished run that has no step for a stage simply did not log one
    const status = grey ? 'not covered' : key in seen ? time(seen[key]!) : run && !run.done ? 'waiting' : 'not logged';
    return { name, key, i, cls, skipped, grey, status };
  });

  return (
    <div className="rlive">
      <div className="rg-head">
        <p className="muted" role="status" aria-atomic="true">
          {run && !run.done ? `Now: ${last?.text ?? 'starting'}.` : row ? `PR #${row.pr_number} · ${row.title || 'Untitled pull request'}` : ''}
        </p>
        <div className="rg-tools">
          <select className="rg-select" aria-label="Pull request" value={id ?? ''} onChange={e => setId(Number(e.target.value))}>
            {prs.map(p => <option key={p.id} value={p.id}>#{p.pr_number} · {p.title || 'Untitled'}</option>)}
          </select>
          {runs.length > 0 && (
            <select className="rg-select" aria-label="Run" value={Math.min(runIx, runs.length - 1)} onChange={e => setRunIx(Number(e.target.value))}>
              {runs.map((r, i) => <option key={i} value={i}>{r.label}</option>)}
            </select>
          )}
          <span className="pill"><i className={'dot' + (run && !run.done ? ' busy' : '')}></i>{run && !run.done ? 'Analysing' : 'Finished'}</span>
        </div>
      </div>

      <section className="rchart">
        <header><h2>Analysis stages</h2><span>{run && !run.done ? 'live from the server: each stage turns green as its step arrives'
                                                                 : 'a stage completes only when its step arrives from the server'}</span></header>
        {/* T-089: one stage after another: the line runs to the next stage, then that stage turns green. A line into or
            out of a stage that was not covered (Defect history, CI) is grey. */}
        <div className={'stepper-wrap' + (run && !run.done ? ' running' : '') + (intro ? ' intro' : '')}>
          <span key={'segs:' + runKey} className="stepper-segs" aria-hidden="true">
            {view.slice(1).map(v => (
              <i key={v.key} className={'stepper-seg' + (v.cls !== 'w' || v.skipped ? ' on' : '') + (view[v.i - 1].grey || v.grey ? ' grey' : '')}
                 style={{ '--i': v.i - 1, left: `${((v.i - 0.5) / STAGES.length) * 100}%`, width: `${100 / STAGES.length}%` } as CSSProperties}><b></b></i>
            ))}
          </span>
        <ol key={'steps:' + runKey} className="stepper">
          {view.map(({ name, key, i, cls, skipped, grey, status }) => {
            return (
              <li key={key} className={'step ' + cls + (grey ? ' x' : '')} style={{ '--i': i } as CSSProperties}
                  aria-current={cls === 'c' ? 'step' : undefined} title={grey ? `${name}: reported, nothing to cover` : undefined}>
                <span className="b">
                  {(cls === 'd' || skipped) && (grey ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 12h10" /></svg>
                                        : <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>)}
                </span>
                <span className="n">{name}</span><span className="t">{status}</span>
                {key === 'history' && history && (
                  <span className={'h ' + row!.defect_history} title={row!.module ? `Module: ${row!.module}` : undefined}
                        aria-label={`Defect history: ${history}${row!.defect_history === 'found' && row!.module ? ` in ${row!.module}` : ''}`}>{history}</span>
                )}
              </li>
            );
          })}
        </ol>
        </div>
      </section>

      <div className="livegrid">
        <section className={'rchart flush' + (run && !run.done ? ' running' : '')}>
          <header>
            <h2>Log {run?.id && <span className="mono muted">· run {run.id.slice(0, 4)}</span>}</h2>
            <div className="seg" role="group" aria-label="Filter log">
              {Object.keys(GROUPS).map(k => <button key={k} aria-pressed={filter === k} onClick={() => setFilter(k)}>{k}</button>)}
            </div>
          </header>
          <div className="console" aria-live="off">
            {error ? <p className="console-note">{error}</p>
              : !past && !current ? <p className="console-note">Reading the saved log</p>
              : !shown.length ? <p className="console-note">No saved steps for this pull request. The trace log keeps the most recent runs only.</p>
              : list.map((m, i) => (
                <div key={m.at + m.event + i} className={'rl-line ' + m.level}>
                  <time>{time(m.at)}</time><span className={'rl-tag ' + m.stage}>{m.stage}</span><span className="rl-text">{m.text}</span>
                </div>
              ))}
            {run && !run.done && <div className="rl-line"><span></span><span></span><span className="cursor" aria-hidden="true"></span></div>}
          </div>
        </section>

        <section className="rchart flush">
            <header><h2>Rules and checks</h2>{rules && row?.score !== null && <span className="mono">{row?.score} pts → {row?.base_label ?? row?.risk_label}</span>}</header>
            {rules && row?.risk_factors.length ? (
              <ul className="checks">{row.risk_factors.map((f, i) => <li key={i}><i className="cdot" aria-hidden="true"></i><span>{f}</span></li>)}</ul>
            ) : <div className="pending">Waiting for the rules stage. Nothing shows until it reports.</div>}
          </section>
      </div>

      {/* T-098: the result and the tests share one row under the log, so nothing waits below an empty column */}
      <div className="liveres">
          <section className="rchart">
            <header><h2>Result and decision</h2></header>
            {run && !run.done ? (
              <div className="decision wait"><b>Waiting for the Manager agent</b><span>Shown when the result is saved.</span></div>
            ) : row?.state === 'scored' && row.risk_label ? (
              <div className={'decision ' + row.risk_label.toLowerCase()}>
                <span className="muted">Decision</span>
                <b><Glyph label={row.risk_label} /> {row.risk_label === 'Low' ? 'Routine change' : 'Test before merging'}</b>
                <span>{row.risk_label} risk{row.score !== null ? `, ${row.score} pts` : ''}. The Manager agent approved the analysis on attempt {row.attempts} of 3.
                  {row.test_areas.length ? ` Run the ${row.test_areas.length} suggested test area${row.test_areas.length === 1 ? '' : 's'} first.` : ''}</span>
              </div>
            ) : row?.state === 'needs_human_review' ? (
              <div className="decision medium"><b>Needs a human review</b><span>The Manager agent did not accept the output after {row.attempts} attempt{row.attempts === 1 ? '' : 's'}. {errorsMsg}</span></div>
            ) : row?.state === 'failed' ? (
              <div className="decision high"><b>The analysis could not finish</b><span>{errorsMsg}</span></div>
            ) : <div className="decision wait"><b>Not decided yet</b><span>{row?.state}</span></div>}
          </section>

          <section className="rchart">
            <header><h2>Tests</h2></header>
            {!!row?.test_areas.length && <div className="rl-chips">{row.test_areas.map((t, i) => <span key={i} className="tchip">{t}</span>)}</div>}
            <div className="pending">Test execution is not built yet (Deliverable 3). Run status appears here once the Test Agent exists.</div>
          </section>
      </div>
    </div>
  );
}
