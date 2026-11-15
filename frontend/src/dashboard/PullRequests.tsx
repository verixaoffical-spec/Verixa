/* T-096 Pull Requests section: every pull request of the connected repository, who opened it, its latest analysis.
 *
 * The list is the saved one (GET /api/analysis/repo-pulls), shown at once from the tab's cache and re-read from GitHub
 * in the background only when the server says it is stale. While the agents work on a pull request, the centre of
 * the section shows that run: every line under it is a real step from the live socket, nothing is scripted here.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api, type Assessment, type LiveEvent, type RepoPull, type RepoPulls } from './api';
import { keep, peek } from './cache';
import { Detail, RiskBadge, ago, hue, initials, type Tab } from './riskParts';

export interface LiveRun { pr: number; messages: LiveEvent[]; done: boolean; finishedAt: number }

const STATE: Record<RepoPull['state'], string> = { open: 'Open', closed: 'Closed', merged: 'Merged' };

// Initials, not GitHub's avatar image: the page loads nothing from GitHub itself (frontend/CLAUDE.md, the CSP)
function Avatar({ pull }: { pull: RepoPull }) {
  return <span className="rpr-avatar" style={{ background: `hsl(${hue(pull.author)} 55% 45%)` }} aria-hidden="true">{initials(pull.author)}</span>;
}

// The run the agents are on right now, in the middle of the section. The core and rings are CSS 3D; the log is real.
export function Processing({ run, title }: { run: LiveRun; title: string | null }) {
  const last = run.messages[run.messages.length - 1];
  const logRef = useRef<HTMLOListElement>(null);
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight }); }, [run.messages.length]);
  return (
    <section className="proc rcard" aria-label={`Verixa is analysing pull request ${run.pr}`}>
      <div className="proc-stage" aria-hidden="true">
        <div className="proc-scene">
          <div className="proc-ring r1"></div>
          <div className="proc-ring r2"></div>
          <div className="proc-ring r3"></div>
          <div className="proc-cube">
            {['f', 'b', 'l', 'r', 't', 'd'].map(face => <i key={face} className={'proc-face ' + face}></i>)}
          </div>
        </div>
      </div>
      <div className="proc-body">
        <p className="proc-kicker"><i className="live-dot" aria-hidden="true"></i>Analysing pull request #{run.pr}</p>
        <h2 className="proc-title">{title || 'Doing calculations…'}</h2>
        <p className="proc-now" role="status" aria-live="polite">{last?.text ?? 'Starting'}</p>
        <p className="proc-log-head">Agent activity<span>Live</span></p>
        <ol className="proc-log" ref={logRef} aria-label="Agent activity">
          {run.messages.map((m, i) => (
            <li key={m.at + m.event + i} className={m.level + (i === run.messages.length - 1 ? ' current' : '')}>
              <time>{new Date(m.at).toLocaleTimeString(undefined, { hour12: false })}</time><span>{m.text}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

interface Props {
  active: boolean;
  items: Assessment[];
  live: LiveRun[];
  onGo: (tab: Tab, analysisId?: number) => void;
}

export default function PullRequests({ active, items, live, onGo }: Props) {
  const [data, setData] = useState<RepoPulls | null>(() => peek<RepoPulls>('pulls') ?? null);
  const [error, setError] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<number | null>(null);

  const save = (next: RepoPulls) => { setData(keep('pulls', next)); setError(''); return next; };
  async function refresh(force: boolean) {
    setSyncing(true);
    try { save(await api.syncPulls(force)); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Could not read the pull requests from GitHub'); }
    finally { setSyncing(false); }
  }

  // First open: the saved list, then GitHub in the background only if that list is stale
  const started = useRef(false);
  useEffect(() => {
    if (!active || started.current) return;
    started.current = true;
    api.repoPulls().then(next => { save(next); if (next.stale) refresh(false); })
      .catch(e => setError(e instanceof ApiError ? e.message : 'Could not load the pull requests'));
  }, [active]);  // eslint-disable-line react-hooks/exhaustive-deps

  // A delivery saves its pull request before the agents start, and a finished run has a new analysis: read the list again
  const runKey = live.map(r => `${r.pr}:${r.done}`).join(',');
  const seenRuns = useRef(runKey);
  useEffect(() => {
    if (!started.current || runKey === seenRuns.current) return;
    seenRuns.current = runKey;
    api.repoPulls().then(save).catch(() => {});
  }, [runKey]);  // eslint-disable-line react-hooks/exhaustive-deps

  // the newest analysis per pull request (the feed is newest first, and a Map keeps the last value set)
  const byNumber = useMemo(() => new Map([...items].reverse().map(a => [a.pr_number, a])), [items]);
  const rows = useMemo(() => {
    const words = q.trim().toLowerCase().replace(/^#/, '');
    const all = data?.items ?? [];
    return words ? all.filter(p => `${p.number} ${p.title ?? ''} ${p.author ?? ''}`.toLowerCase().includes(words)) : all;
  }, [data, q]);
  const running = live.filter(r => !r.done);

  return (
    <div className="rgrid">
      {running.map(run => (
        <Processing key={run.pr} run={run} title={data?.items.find(p => p.number === run.pr)?.title ?? byNumber.get(run.pr)?.title ?? null} />
      ))}

      <section className="rcard rtable" aria-label="Pull Requests on GitHub">
        <div className="prs-head">
          <h2 className="rcard-title">Pull Requests</h2>
          <div className="prs-tools">
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

        {!data ? (
          <div className="empty"><b>Loading</b>Reading the saved pull requests.</div>
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
                        <div className="rpr-meta">{p.draft ? 'draft · ' : ''}{p.head_sha ? <code>{p.head_sha.slice(0, 7)}</code> : null}</div>
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
