/* T-096 Pull Requests section: every pull request of the connected repository, who opened it, its latest analysis.
 *
 * The list is the saved one (GET /api/analysis/repo-pulls), shown at once from the tab's cache and re-read from GitHub
 * in the background only when the server says it is stale. While the agents work on a pull request, the centre of
 * the section shows that run: every line under it is a real step from the live socket, nothing is scripted here.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api, type Assessment, type LiveEvent, type RepoPull, type RepoPulls, type Stage } from './api';
import { keep, peek } from './cache';
import { Detail, RiskBadge, ago, hue, initials, type Tab } from './riskParts';
import AgentScene, { AgentStrip, agentOf, type AgentName } from './AgentScene';

// startedAt: when the run's first step happened. Fixed for the run's life (the kept messages are capped at 30, so the first
// kept message is not a stable name for the run): it keys the card and drives its clock.
export interface LiveRun { pr: number; messages: LiveEvent[]; done: boolean; finishedAt: number; startedAt: number }

const STATE: Record<RepoPull['state'], string> = { open: 'Open', closed: 'Closed', merged: 'Merged' };

// Initials, not GitHub's avatar image: the page loads nothing from GitHub itself (frontend/CLAUDE.md, the CSP)
function Avatar({ pull }: { pull: RepoPull }) {
  return <span className="rpr-avatar" style={{ background: `hsl(${hue(pull.author)} 55% 45%)` }} aria-hidden="true">{initials(pull.author)}</span>;
}

const STAGE_ORDER: Stage[] = ['received', 'changes', 'history', 'ci', 'rules', 'model', 'manager', 'saved'];
const AGENT_TAG: Record<AgentName, string> = { manager: 'Manager', analysis: 'Analysis', test: 'Test' };
const HOLD_MS = 8000;   // T-089: a finished run stays on screen this long, showing its result, before it folds away
const FOLD_MS = 700;    // the fold animation, premium.css (.proc-wrap.leaving)

const clock = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};

/** T-089: the runs to show in a processing card: every run going on, and a run that finished here a moment ago
 * (not one replayed after a reload), held for HOLD_MS with its result so the card never vanishes mid-glance. */
export function useShownRuns(live: LiveRun[]): { run: LiveRun; leaving: boolean; hide: () => void }[] {
  const [now, setNow] = useState(() => Date.now());
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const fresh = (r: LiveRun) => r.done && !r.messages[r.messages.length - 1]?.replay && Date.now() - r.finishedAt < HOLD_MS + FOLD_MS;
  const holding = live.some(fresh);
  useEffect(() => {  // tick while a finished run is held, so it folds and leaves on time
    if (!holding) return;
    const t = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(t);
  }, [holding]);
  const key = (r: LiveRun) => `${r.pr}:${r.startedAt}`;
  return live.filter(r => (!r.done || fresh(r)) && !hidden.has(key(r))).map(r => ({
    run: r,
    leaving: r.done && now - r.finishedAt >= HOLD_MS,
    hide: () => setHidden(h => new Set(h).add(key(r))),
  }));
}

// The run the agents are on right now, in the middle of the section. T-089: the working agent's own animation (CSS),
// chosen from the last real step; a progress bar over the real stages reached; a running clock; the log is real.
// When the run finishes the card shows its result for a moment, then folds away smoothly.
export function Processing({ run, title, result, leaving = false, onHide }:
  { run: LiveRun; title: string | null; result?: Assessment | null; leaving?: boolean; onHide?: () => void }) {
  const last = run.messages[run.messages.length - 1];
  const done = run.done;
  // how the run ended, from its last real step: approved and saved, saved for a human review, or stopped
  const outcome: 'ok' | 'review' | 'stopped' = last?.level === 'error' ? 'stopped' : last?.level === 'warn' ? 'review' : 'ok';
  const ok = outcome === 'ok';
  const agent = agentOf(last);
  const logRef = useRef<HTMLOListElement>(null);
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' }); }, [run.messages.length]);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (done) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [done]);
  const started = run.startedAt;
  const elapsed = (done ? new Date(last.at).getTime() : now) - started;
  const reached = Math.max(0, ...run.messages.map(m => STAGE_ORDER.indexOf(m.stage)));
  const progress = done ? 1 : (reached + 1) / STAGE_ORDER.length;
  return (
    <div className={'proc-wrap' + (leaving ? ' leaving' : '')}>
      <section className={'proc rcard' + (done ? ' done' + (ok ? '' : ' ' + outcome) : '')} data-agent={done ? 'done' : agent}
               aria-label={done ? `Verixa finished pull request ${run.pr}` : `Verixa is analysing pull request ${run.pr}`}>
        <span className="proc-progress" aria-hidden="true"><i style={{ transform: `scaleX(${progress})` }}></i></span>
        <div className="proc-agent">
          <AgentScene agent={agent} done={done} outcome={outcome} />
        </div>
        <div className="proc-body">
          <div className="proc-top">
            <p className="proc-kicker">
              {done ? <i className={'proc-tick ' + outcome} aria-hidden="true"></i> : <i className="live-dot" aria-hidden="true"></i>}
              {!done ? `Analysing pull request #${run.pr}` : ok ? `Analysis complete · pull request #${run.pr}`
                : outcome === 'review' ? `Needs a human review · pull request #${run.pr}` : `Stopped · pull request #${run.pr}`}
            </p>
            <span className="proc-clock" title={done ? 'How long the run took' : 'Time since GitHub delivered it'}>{clock(elapsed)}</span>
            {done && onHide && <button className="proc-hide" onClick={onHide} aria-label={`Hide pull request ${run.pr}`}>Hide</button>}
          </div>
          {done ? (
            <div className="proc-result">
              {result?.risk_label ? <RiskBadge label={result.risk_label} /> : null}
              {result?.score !== null && result?.score !== undefined ? <span className="mono muted">{result.score} pts</span> : null}
              <span className="muted">{last?.text}</span>
            </div>
          ) : <AgentStrip agent={agent} />}
          <h2 className="proc-title">{title || 'Doing calculations…'}</h2>
          {!done && <p className="proc-now" role="status" aria-live="polite">{last?.text ?? 'Starting'}</p>}
          <p className="proc-log-head">Agent activity<span className={done ? 'off' : ''}>{done ? 'Done' : 'Live'}</span></p>
          <ol className="proc-log" ref={logRef} aria-label="Agent activity">
            {run.messages.map((m, i) => {
              const who = agentOf(m);
              return (
                <li key={m.at + m.event + i} className={m.level + (i === run.messages.length - 1 && !done ? ' current' : '')}>
                  <time>{new Date(m.at).toLocaleTimeString(undefined, { hour12: false })}</time>
                  <b className={'proc-who ' + who}>{AGENT_TAG[who]}</b><span>{m.text}</span>
                </li>
              );
            })}
          </ol>
        </div>
      </section>
    </div>
  );
}

interface Props {
  active: boolean;
  items: Assessment[];
  live: LiveRun[];
  onGo: (tab: Tab, analysisId?: number) => void;
}

// T-099: each branch's list is kept apart in the tab's cache, so switching back to a branch shows it at once
const cacheKey = (branch: string) => (branch ? `pulls:${branch}` : 'pulls');

export default function PullRequests({ active, items, live, onGo }: Props) {
  const [data, setData] = useState<RepoPulls | null>(() => peek<RepoPulls>('pulls') ?? null);
  const [error, setError] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<number | null>(null);
  const [branch, setBranch] = useState('');
  const branchNow = useRef('');  // the selection an answer must match, so a slow answer for another branch is not shown
  const [branches, setBranches] = useState<RepoPulls['branches']>(() => data?.branches ?? []);

  const save = (next: RepoPulls) => {
    keep(cacheKey(next.branch ?? ''), next);
    setBranches(next.branches);
    if ((next.branch ?? '') === branchNow.current) { setData(next); setError(''); }
    return next;
  };
  function pickBranch(next: string) {
    branchNow.current = next;
    setBranch(next);
    setOpen(null);
    setData(peek<RepoPulls>(cacheKey(next)) ?? null);
    api.repoPulls(next).then(save)
      .catch(e => { if (branchNow.current === next) setError(e instanceof ApiError ? e.message : 'Could not load the pull requests'); });
  }
  async function refresh(force: boolean) {
    setSyncing(true);
    try { save(await api.syncPulls(force, branchNow.current)); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Could not read the pull requests from GitHub'); }
    finally { setSyncing(false); }
  }

  // First open: the saved list, then GitHub in the background only if that list is stale
  const started = useRef(false);
  useEffect(() => {
    if (!active || started.current) return;
    started.current = true;
    api.repoPulls(branchNow.current).then(next => { save(next); if (next.stale) refresh(false); })
      .catch(e => setError(e instanceof ApiError ? e.message : 'Could not load the pull requests'));
  }, [active]);  // eslint-disable-line react-hooks/exhaustive-deps

  // A delivery saves its pull request before the agents start, and a finished run has a new analysis: read the list again
  const runKey = live.map(r => `${r.pr}:${r.done}`).join(',');
  const seenRuns = useRef(runKey);
  useEffect(() => {
    if (!started.current || runKey === seenRuns.current) return;
    seenRuns.current = runKey;
    api.repoPulls(branchNow.current).then(save).catch(() => {});
  }, [runKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  // the newest analysis per pull request (the feed is newest first, and a Map keeps the last value set)
  const byNumber = useMemo(() => new Map([...items].reverse().map(a => [a.pr_number, a])), [items]);
  const rows = useMemo(() => {
    const words = q.trim().toLowerCase().replace(/^#/, '');
    const all = data?.items ?? [];
    return words ? all.filter(p => `${p.number} ${p.title ?? ''} ${p.author ?? ''}`.toLowerCase().includes(words)) : all;
  }, [data, q]);
  const shown = useShownRuns(live);  // T-089: a finished run stays a moment with its result, then folds away

  return (
    <div className="rgrid">
      {shown.map(({ run, leaving, hide }) => (
        <Processing key={run.pr + ':' + run.startedAt} run={run} leaving={leaving} onHide={hide} result={byNumber.get(run.pr) ?? null}
                    title={data?.items.find(p => p.number === run.pr)?.title ?? byNumber.get(run.pr)?.title ?? null} />
      ))}

      <section className="rcard rtable" aria-label="Pull Requests on GitHub">
        <div className="prs-head">
          <h2 className="rcard-title">Pull Requests</h2>
          <div className="prs-tools">
            <select className="rg-select prs-branch-pick" aria-label="Branch" value={branch} onChange={e => pickBranch(e.target.value)}>
              <option value="">All branches</option>
              {branches.map(b => <option key={b.name} value={b.name}>{b.name} · {b.pulls} PR{b.pulls === 1 ? '' : 's'}</option>)}
            </select>
            <input type="search" className="prs-search" value={q} onChange={e => setQ(e.target.value)}
                   placeholder="Search by number, title or author" aria-label="Search pull requests" />
            <button className="btn ghost sm" onClick={() => refresh(true)} disabled={syncing}>
              {syncing ? 'Checking GitHub…' : 'Refresh from GitHub'}
            </button>
          </div>
          <p className="muted prs-sub" role="status">
            {data?.listed_at ? `Listed from GitHub ${ago(data.listed_at)}` : syncing ? 'Reading the list from GitHub' : ''}
          </p>
        </div>
        {error && <div className="warnbox prs-warn" role="alert">{error}</div>}

        {!data && error ? null : !data ? (
          <div className="empty"><b>Loading</b>Reading the saved pull requests.</div>
        ) : !data.items.length && branch ? (
          <div className="empty"><b>No pull requests on {branch}</b>No saved pull request comes from or goes into this branch.</div>
        ) : !data.items.length ? (
          <div className="empty"><b>No pull requests yet</b>{syncing ? 'Reading them from GitHub.' : 'Open one on GitHub and it appears here.'}</div>
        ) : !rows.length ? (
          <div className="empty"><b>No match</b>No pull request matches “{q.trim()}”.</div>
        ) : (
          <div className="tablewrap">
            <table className="grid risk-grid prs-grid">
              <thead>
                <tr><th>Pull request</th><th>Author</th><th>Risk</th><th>Status</th><th className="ract">Updated</th></tr>
              </thead>
              {rows.map(p => {
                const a = byNumber.get(p.number);
                const isOpen = open === p.number;
                return (
                  <tbody key={p.number}>
                    <tr className={'risk-row' + (isOpen ? ' open' : '')} tabIndex={0} aria-expanded={isOpen}
                        onClick={() => setOpen(isOpen ? null : p.number)}
                        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(isOpen ? null : p.number); } }}>
                      <td>
                        <div className="rpr-title"><b>#{p.number}</b>{p.title || 'Untitled pull request'}</div>
                        <div className="rpr-meta">
                          {p.draft ? 'draft · ' : ''}{p.head_sha ? <code>{p.head_sha.slice(0, 7)}</code> : null}
                          {p.head_ref && p.base_ref && (
                            <span className="prs-branches" aria-label={`from branch ${p.head_ref} into ${p.base_ref}`}>
                              <code className={'prs-ref' + (p.head_ref === branch ? ' on' : '')} title="Source branch">{p.head_ref}</code>
                              <span aria-hidden="true">→</span>
                              <code className={'prs-ref' + (p.base_ref === branch ? ' on' : '')} title="Target branch">{p.base_ref}</code>
                            </span>
                          )}
                        </div>
                      </td>
                      <td><div className="rpr"><Avatar pull={p} /><span className="prs-author">{p.author ?? 'unknown'}</span></div></td>
                      <td>{a ? <RiskBadge label={a.risk_label} /> : <span className="muted">Not analysed</span>}</td>
                      <td><span className={'prs-state ' + p.state}>{STATE[p.state]}</span></td>
                      <td className="ract"><span className="muted">{ago(p.updated_at)}</span></td>
                    </tr>
                    {isOpen && (a ? <Detail row={a} history={items.filter(r => r.pr_number === p.number)} onGo={tab => onGo(tab, a.id)} /> : (
                      <tr><td className="rdetail" colSpan={5}><div className="rdetail-in">
                        <p className="muted">Verixa has not analysed this pull request. It is analysed when GitHub delivers a push to it, or with Analyse now on the Overview.</p>
                        <div className="rmeta">
                          {p.created_at && <span className="muted">opened {ago(p.created_at)} by {p.author ?? 'unknown'}</span>}
                          {p.url && <a className="btn ghost sm" href={p.url} target="_blank" rel="noopener noreferrer">Open on GitHub</a>}
                        </div>
                      </div></td></tr>
                    ))}
                  </tbody>
                );
              })}
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
