/* Risk Analysis — Deliverable 2.
 *
 * Shows what the Analysis Agent produced for every pull request on the connected repository:
 * the rule-based risk label and score, the rule trace that justifies it, the agent's reasoning
 * and its suggested test areas.
 *
 * Nothing on this screen is invented. Every value is read from /api/analysis/pull-requests, which
 * reads the risk_assessments rows the agent wrote. A pull request that has not been scored yet
 * shows its real state (queued, running, needs review, failed), never a placeholder label.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { ApiError, api, openLive, type LiveEvent, type RiskFeed, type RiskLabel } from './api';
import { icons } from './icons';
import { Chip, hookLabel, type HookState, type Link } from './connection';
import { useToast } from './Toast';
import { RiskCharts } from './RiskCharts';
import RiskTrend from './RiskTrend';
import RiskGraph from './RiskGraph';
import RiskLive from './RiskLive';
import { keep, peek } from './cache';
import PullRequests, { Processing, Skeleton, useShownRuns, type LiveRun } from './PullRequests';
import OverviewTop from './OverviewTop';
import { agentOf } from './AgentScene';
import { Detail, RiskBadge, STATE_TEXT, StateBadge, ago, hue, initials, type Tab } from './riskParts';

interface Props {
  hidden: boolean;
  link: Link | null;
  hook: HookState;
  onGoConnect: () => void;
}

const POLL_MS = 4000;
const TABS: [Tab, string][] = [['prs', 'Pull Requests'], ['overview', 'Overview'], ['graph', 'Dependency graph'], ['live', 'Live runs and logs']];
const LIVE_KEEP_MS = 2 * 60 * 1000;  // a finished run stays on screen this long

function addLive(runs: LiveRun[], event: LiveEvent): LiveRun[] {
  const current = runs.find(r => r.pr === event.pr);
  const startsNew = event.event === 'service.delivery' || event.event === 'run.start';
  // A message after a finished run starts a new one, unless it is a replay of what is already shown
  if (!current || (current.done && startsNew && !current.messages.some(m => m.at === event.at && m.event === event.event))) {
    const fresh = { pr: event.pr, messages: [event], done: event.done, finishedAt: event.done ? Date.now() : 0,
                    startedAt: Date.parse(event.at) || Date.now() };
    return [fresh, ...runs.filter(r => r.pr !== event.pr)];
  }
  if (current.messages.some(m => m.at === event.at && m.event === event.event)) return runs;  // already shown
  const next = { ...current, messages: [...current.messages, event].slice(-30),
                 done: current.done || event.done, finishedAt: event.done ? Date.now() : current.finishedAt };
  return runs.map(r => (r === current ? next : r));
}

function LivePanel({ runs, onClose }: { runs: LiveRun[]; onClose: (pr: number) => void }) {
  if (!runs.length) return null;
  return (
    <div className="live" aria-live="polite">
      {runs.map(run => {
        const last = run.messages[run.messages.length - 1];
        return (
          <section key={run.pr} className={'live-run' + (run.done ? ' done ' + last.level : '')}
                   aria-label={`Agents working on pull request ${run.pr}`}>
            <header className="live-head">
              <b>PR #{run.pr}</b>
              <span className="live-status">
                {!run.done && <i className="live-dot" aria-hidden="true"></i>}
                {run.done ? (last.level === 'ok' ? 'Finished' : last.level === 'error' ? 'Stopped' : 'Finished, check the result') : 'Agents are analysing'}
              </span>
              {run.done && <button className="live-close" onClick={() => onClose(run.pr)} aria-label={`Hide PR #${run.pr}`}>×</button>}
            </header>
            <ol className="live-steps">
              {run.messages.map((m, i) => (
                <li key={m.at + m.event + i} className={m.level + (!run.done && i === run.messages.length - 1 ? ' current' : '')}>
                  {m.text}
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </div>
  );
}

// The Risk views' tab bar. T-098: a frosted glass indicator measures the selected tab and glides to it.
function ViewTabs({ tab, go, hidden }: { tab: Tab; go: (next: Tab) => void; hidden: boolean }) {
  const bar = useRef<HTMLDivElement>(null);
  const [ind, setInd] = useState<{ x: number; w: number } | null>(null);
  useLayoutEffect(() => {
    const el = bar.current;
    if (!el || hidden) return;
    const place = () => {
      const on = el.querySelector<HTMLButtonElement>('[aria-selected="true"]');
      if (on && on.offsetWidth) setInd({ x: on.offsetLeft, w: on.offsetWidth });
    };
    place();
    const watch = new ResizeObserver(place);  // fonts loading, a narrower window, or the screen being shown again
    watch.observe(el);
    const on = el.querySelector('[aria-selected="true"]');
    if (on) watch.observe(on);  // the tab itself can change size while the bar does not (the bar scrolls when clipped)
    return () => watch.disconnect();
  }, [tab, hidden]);
  return (
    <div ref={bar} className={'rnav' + (ind ? ' measured' : '')} role="tablist" aria-label="Risk Analysis views" onKeyDown={e => {
      // arrow keys, Home and End move between the views (WAI-ARIA tabs pattern)
      const i = TABS.findIndex(([key]) => key === tab);
      const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
      if (next === undefined) return;
      e.preventDefault();
      const key = TABS[(next + TABS.length) % TABS.length][0];
      go(key);
      e.currentTarget.querySelector<HTMLButtonElement>(`[data-tab="${key}"]`)?.focus();
    }}>
      {ind && <span className="rnav-ind" aria-hidden="true" style={{ width: ind.w, transform: `translateX(${ind.x}px)` }}></span>}
      {TABS.map(([key, label]) => (
        <button key={key} role="tab" data-tab={key} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1}
                onClick={() => go(key)}>{label}</button>
      ))}
    </div>
  );
}

export default function RiskView({ hidden, link, hook, onGoConnect }: Props) {
  const toast = useToast();
  const [feed, setFeed] = useState<RiskFeed | null>(() => peek<RiskFeed>('feed') ?? null);  // T-096: last feed, at once
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [prNumber, setPrNumber] = useState('');
  const [busy, setBusy] = useState(false);
  const asking = useRef(false);  // T-089: an Analyse now from this page is waiting for its answer
  const [tab, setTab] = useState<Tab>(() => peek<Tab>('tab') ?? 'prs');
  const go = (next: Tab) => setTab(keep('tab', next));  // a reload comes back to the same view

  const load = useCallback(async (): Promise<RiskFeed | null> => {
    try {
      const next = await api.riskFeed();
      setFeed(keep('feed', next));
      setFailed(false);
      return next;
    } catch (err) {
      // A 401 is handled globally by App.tsx. Anything else leaves the last good data on screen.
      if (!(err instanceof ApiError) || err.status !== 401) setFailed(true);
      return null;
    }
  }, []);

  // Load once when the screen is first opened, not while it is hidden behind another view
  const loaded = useRef(false);
  useEffect(() => {
    if (hidden || loaded.current || !link) return;
    loaded.current = true;
    load();
  }, [hidden, link, load]);

  // Live status over the WebSocket: each agent step arrives as it happens, for the connected repository
  const [liveRuns, setLiveRuns] = useState<LiveRun[]>([]);
  const [liveOn, setLiveOn] = useState(false);
  const shownRuns = useShownRuns(liveRuns);  // T-089: a hook, so above every early return (React keeps hook order)
  const repo = link?.repo;
  useEffect(() => {
    if (!repo) return;
    setLiveRuns([]);
    return openLive(event => {
      if (event.repo !== repo) return;
      setLiveRuns(runs => addLive(runs, event));
      if (event.done && !event.replay) {  // the saved result is in the list now
        if (asking.current) { load(); return; }  // Analyse now on this page already says how it went
        load().then(next => {
          // T-089: say so, wherever in the app the person is, with a way to the pull request
          const row = next?.items.find(r => r.pr_number === event.pr);
          toast(row?.state === 'scored' && row.risk_label ? `PR #${event.pr} analysed: ${row.risk_label} risk` : `PR #${event.pr}: ${event.text}`,
                { label: 'View', run: () => { setTab(keep('tab', 'prs')); location.hash = 'risk'; } });  // App follows the hash
        });
      }
      // T-089: a new run's pull request is saved (queued) before the agents start, so read the list again at once.
      // Live runs and logs can then follow its stages from the socket as they arrive, even for a brand-new pull request.
      else if (!event.replay && (event.event === 'service.delivery' || event.event === 'run.start')) load();
    }, setLiveOn);
  }, [repo, load]);

  // Finished runs fade out of the panel after a while
  useEffect(() => {
    if (!liveRuns.some(r => r.done)) return;
    const timer = setInterval(() => {
      setLiveRuns(runs => runs.filter(r => !r.done || Date.now() - r.finishedAt < LIVE_KEEP_MS));
    }, 10000);
    return () => clearInterval(timer);
  }, [liveRuns]);

  // Poll only while something is actually being scored, and only while this screen is visible
  const pending = (feed?.counts.pending ?? 0) > 0;
  useEffect(() => {
    if (hidden || !pending) return;
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [hidden, pending, load]);

  if (!link) {
    return (
      <section hidden={hidden} className="lock-wrap">
        <article className="lock">
          <span className="lock-ico">{icons.integrations}</span>
          <h2>Connect a repository first</h2>
          <p>Risk Analysis reads the pull requests of a connected repository. Link GitHub and Jira once to set it up.</p>
          <div><button className="btn" onClick={onGoConnect}>Go to Integrations</button></div>
        </article>
      </section>
    );
  }

  async function analyse() {
    const number = Number(prNumber.trim());
    if (!Number.isInteger(number) || number < 1) {
      toast('Enter the pull request number, for example 4');
      return;
    }
    setBusy(true);
    asking.current = true;
    try {
      const row = await api.analysePr(number);
      await load();
      setOpen(row.id);
      toast(
        row.state === 'scored'
          ? `#${row.pr_number} scored ${row.risk_label}`
          : `#${row.pr_number}: ${STATE_TEXT[row.state].toLowerCase()}`,
      );
      setPrNumber('');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'The analysis could not be started';
      toast(message.slice(0, 200));
    } finally {
      setBusy(false);
      asking.current = false;
    }
  }

  const items = feed?.items ?? [];
  const counts = feed?.counts ?? {};
  const running = liveRuns.filter(r => !r.done);
  // The graph and log follow the opened PR, at its newest analysis (the feed is newest first)
  const latestOpen = items.find(r => r.pr_number === items.find(x => x.id === open)?.pr_number)?.id ?? null;
  const tiles: { key: RiskLabel | 'total'; cls: string; label: string; icon: typeof icons.bolt; sub: string }[] = [
    { key: 'total', cls: '', label: 'Pull Requests', icon: icons.pullRequests, sub: 'seen by the agent' },
    { key: 'High', cls: 'high', label: 'High risk', icon: icons.alert, sub: 'test these first' },
    { key: 'Medium', cls: 'med', label: 'Medium risk', icon: icons.bolt, sub: 'worth a look' },
    { key: 'Low', cls: 'low', label: 'Low risk', icon: icons.library, sub: 'routine change' },
  ];

  return (
    <section hidden={hidden} className="workspace risk">
      <ViewTabs tab={tab} go={go} hidden={hidden} />

      <header className="rpage-head">
        <div>
          <h1>Risk Analysis</h1>
          <p className="lead">
            Every pull request on <b className="mono">{link.repo}</b> is scored automatically when GitHub
            delivers it. The label comes from rules in code; the agent writes the reasoning and the
            test areas.
          </p>
        </div>
        <div className="chips">
          <span title={items[0]?.created_at ? `Last analysis ${ago(items[0].created_at) || 'just now'}` : undefined}>
            <Chip on={hook === 'ok'}>{hookLabel(hook)}{items[0]?.created_at ? ` · ${ago(items[0].created_at) || 'just now'}` : ''}</Chip>
          </span>
          <Chip on={liveOn}>{liveOn ? 'Live updates on' : 'Live updates connecting'}</Chip>
          {feed && <Chip on={false}>Jira {link.jiraKey}</Chip>}
          {(counts.needs_review ?? 0) > 0 && <Chip on={false}>{counts.needs_review} need review</Chip>}
          {(counts.failed ?? 0) > 0 && <Chip on={false}>{counts.failed} failed</Chip>}
        </div>
      </header>

      {/* T-096: every view stays mounted, so switching back shows what it already read without asking again */}
      <div className="rpanel" role="tabpanel" aria-label="Pull Requests" hidden={tab !== 'prs'}>
        {/* T-089: Analyse now lives with the pull requests it scores (it was on the Overview) */}
          <section className="rcard" aria-label="Analyse a pull request">
            <h2 className="rcard-title">Analyse a pull request</h2>
            <div className="risk-ask">
              <input value={prNumber} onChange={e => setPrNumber(e.target.value.replace(/\D/g, '').slice(0, 7))}
                     onKeyDown={e => { if (e.key === 'Enter' && !busy) analyse(); }}
                     placeholder="PR #" aria-label="Pull request number" inputMode="numeric" disabled={busy} />
              <button className="btn" onClick={analyse} disabled={busy || !prNumber.trim()}>
                {busy ? 'Analysing…' : 'Analyse now'}
              </button>
              <span className="hint">
                {busy ? 'The agent is reading the diff and scoring it. This takes a few seconds.'
                      : 'Scores a pull request without waiting for a webhook delivery.'}
              </span>
            </div>
          </section>
        <PullRequests active={!hidden && tab === 'prs'} items={items} live={liveRuns}
                      onGo={(next, id) => { if (id) setOpen(id); go(next); }} />
      </div>
      <div className="rcard rpanel" role="tabpanel" aria-label="Dependency graph" hidden={tab !== 'graph'}>
        <RiskGraph items={items} pick={latestOpen} active={!hidden && tab === 'graph'} />
      </div>
      <div className="rcard rpanel" role="tabpanel" aria-label="Live runs and logs" hidden={tab !== 'live'}>
        <RiskLive items={items} live={liveRuns} pick={latestOpen} active={!hidden && tab === 'live'} />
      </div>
      <div className="rgrid rpanel" role="tabpanel" aria-label="Overview" hidden={tab !== 'overview'}>
        {hook !== 'ok' && (
          <div className="warnbox">
            GitHub has not delivered anything to this webhook yet, so nothing will arrive on its own.
            Check Integrations, or score a pull request by number on the Pull Requests tab.
          </div>
        )}
        {failed && (
          <div className="warnbox">
            Could not reach the Verixa server. The list below may be out of date.
          </div>
        )}

        {/* T-089: a run going on shows here too, with the working agent's animation, so Analyse now is seen working */}
        {shownRuns.map(({ run, leaving, hide }) => (
          <Processing key={run.pr + ':' + run.startedAt} run={run} leaving={leaving} onHide={hide}
                      result={items.find(r => r.pr_number === run.pr) ?? null} title={items.find(r => r.pr_number === run.pr)?.title ?? null} />
        ))}

        {/* T-089: the reference's layout: hero and Agents, then goal cards with rings, then the area chart */}
        <OverviewTop items={items} counts={counts} ready={feed?.agent_available ?? true}
                     working={running.length ? agentOf(running[0].messages[running[0].messages.length - 1]) : null} />

        <div className="risk-stats goals">
          {tiles.map(tile => {
            // a ring with the card's share: of all pull requests for a label, the scored share for the total
            const all = counts.total ?? 0;
            const part = tile.key === 'total' ? counts.scored ?? 0 : counts[tile.key] ?? 0;
            const pct = all ? Math.round((part / all) * 100) : 0;
            const newest = items.find(r => tile.key === 'total' || r.risk_label === tile.key);
            return (
              <div key={tile.key} className={'risk-stat rcard goal ' + tile.cls}>
                <div className="goal-top">
                  <span className="goal-ico" aria-hidden="true">{tile.icon}</span>
                  <span className="goal-chip">{newest ? ago(newest.updated_at) || 'saved' : 'none yet'}</span>
                </div>
                <span className="risk-ring big" role="img" style={{ '--p': pct } as CSSProperties}
                      aria-label={tile.key === 'total' ? `${pct}% scored` : `${pct}% of pull requests`}>
                  <svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="18" pathLength={100} />{pct > 0 && <circle className="on" cx="22" cy="22" r="18" pathLength={100} />}</svg>
                  <b>{pct}%</b><small>{tile.key === 'total' ? 'scored' : 'of PRs'}</small>
                </span>
                <div className="risk-stat-label">{tile.label}</div>
                <div className="goal-line">
                  <b className="risk-stat-value">{counts[tile.key] ?? 0}</b>
                  {tile.key === 'total' ? ' PRs in all' : ` of ${all} PR${all === 1 ? '' : 's'}`}
                </div>
                <div className="risk-stat-sub">{tile.sub}</div>
                <button className="goal-btn" onClick={() => go('prs')}>View PRs</button>
              </div>
            );
          })}
        </div>



        <LivePanel runs={liveRuns.filter(r => r.done)} onClose={pr => setLiveRuns(runs => runs.filter(r => r.pr !== pr))} />

        {feed && items.length > 0 && <RiskCharts items={items} counts={counts} trend={<RiskTrend items={items} />} />}

        <section className="rcard rtable" aria-label="Pull Requests">
          <h2 className="rcard-title">Pull Requests</h2>
        {!feed ? (
          <Skeleton rows={5} label="Reading the agent's assessments" />
        ) : !items.length ? (
          <div className="empty">
            <b>No pull requests analysed yet</b>
            Open or push to a pull request on {link.repo}, or score it by number on the Pull Requests tab.
          </div>
        ) : (
          <div className="tablewrap">
            <table className="grid risk-grid">
              <thead>
                <tr>
                  <th>Pull request</th>
                  <th>Risk</th>
                  <th className="rscore">Score</th>
                  <th>Status</th>
                  <th className="ract">Analysed</th>
                </tr>
              </thead>
              {items.map(row => (
                <tbody key={row.id}>
                  <tr className={'risk-row' + (open === row.id ? ' open' : '')}
                      onClick={() => setOpen(open === row.id ? null : row.id)}
                      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(open === row.id ? null : row.id); } }}
                      tabIndex={0} aria-expanded={open === row.id}>
                    <td>
                      <div className="rpr">
                        <span className="rpr-avatar" style={{ background: `hsl(${hue(row.author)} 55% 45%)` }}>
                          {initials(row.author)}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <div className="rpr-title"><b>#{row.pr_number}</b>{row.title || 'Untitled pull request'}</div>
                          <div className="rpr-meta">
                            {row.module ? `${row.module} · ` : ''}
                            {row.files_changed !== null ? `${row.files_changed} file${row.files_changed === 1 ? '' : 's'} · ` : ''}
                            <code>{row.head_sha.slice(0, 7)}</code>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td><RiskBadge label={row.risk_label} /></td>
                    <td className="rscore">{row.score ?? '—'}</td>
                    <td><StateBadge state={row.state} /></td>
                    <td className="ract"><span className="muted">{ago(row.updated_at)}</span></td>
                  </tr>
                  {open === row.id && <Detail row={row} history={items.filter(r => r.pr_number === row.pr_number)} onGo={go} />}
                </tbody>
              ))}
            </table>
          </div>
        )}
        </section>
      </div>
    </section>
  );
}
