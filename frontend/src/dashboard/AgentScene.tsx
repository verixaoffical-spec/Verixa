/* T-089 Which agent is working, drawn in the live processing view. Each agent has its own animation and the stage
 * moves between them smoothly as the live socket reports steps:
 *   Manager  — the supervisor: a shielded core with its workers in orbit, reporting back to it, under a radar sweep.
 *   Analysis — scoring: a risk gauge filling from low to high while a scanner reads the changed lines.
 *   Test     — finding defects and executing: test cases run one by one, one fails and a target locks on to it.
 * The agent shown is read from the real event name, never guessed. The Test agent's scene shows once it sends steps.
 */
import type { LiveEvent } from './api';

export type AgentName = 'manager' | 'analysis' | 'test';

export const AGENTS: [AgentName, string, string][] = [
  ['manager', 'Manager', 'supervising the run'],
  ['analysis', 'Analysis', 'scoring the risk'],
  ['test', 'Test', 'running tests, finding defects'],
];

/** The agent a live step belongs to: GitHub reads, rules and the model call are the Analysis agent's work, test.* the
 * Test agent's, and the delivery, hand-offs, validation, retries and saving are the Manager's. */
export function agentOf(m: LiveEvent | undefined): AgentName {
  const e = m?.event ?? '';
  if (e.startsWith('test.')) return 'test';
  if (/^(github|rules|analysis|ci)\./.test(e)) return 'analysis';
  return 'manager';
}

function Manager() {
  return (
    <>
      <span className="ag-sweep"></span>
      <span className="ag-halo"></span>
      <span className="ag-orbit">
        {[0, 1, 2].map(i => <span key={i} className={'ag-sat s' + i}><i></i></span>)}
      </span>
      <span className="ag-core mgr">
        <svg viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 4.4-3 8.3-7 9.5C8 19.3 5 15.4 5 11V6z" /><path d="M9 12l2 2 4-4" /></svg>
      </span>
    </>
  );
}

function Analysis() {
  return (
    <>
      <svg className="ag-gauge" viewBox="0 0 120 120">
        <circle className="trk" cx="60" cy="60" r="50" />
        {Array.from({ length: 24 }, (_, i) => <line key={i} className="tick" x1="60" y1="4" x2="60" y2={i % 6 === 0 ? 11 : 8} transform={`rotate(${i * 15} 60 60)`} />)}
      </svg>
      <span className="ag-dial"></span>
      <span className="ag-needle"></span>
      <span className="ag-lines">
        {[78, 54, 90, 40, 66].map((w, i) => <i key={i} style={{ width: w + '%' }}></i>)}
        <b className="ag-scan"></b>
      </span>
    </>
  );
}

function Test() {
  return (
    <>
      <span className="ag-cases">
        {Array.from({ length: 9 }, (_, i) => <i key={i} className={'c' + i + (i === 5 ? ' bug' : '')}></i>)}
      </span>
      <span className="ag-lock"><i></i><i></i><i></i><i></i></span>
      <span className="ag-run"><i></i></span>
      <span className="ag-core tst">
        <svg viewBox="0 0 24 24"><path d="M8 5.5v13l10.5-6.5z" /></svg>
      </span>
    </>
  );
}

export type Outcome = 'ok' | 'review' | 'stopped';
const MARK: Record<Outcome, string> = {
  ok: 'M40 61l14 14 27-30',          // approved and saved: a check
  review: 'M60 36v30M60 82v.5',      // saved for a human review: an exclamation
  stopped: 'M44 44l32 32M76 44L44 76', // stopped: a cross
};

/** The run is over: a ring closes in the outcome's colour and its mark draws in; an approved run also gets a soft burst. */
function Done({ outcome }: { outcome: Outcome }) {
  return (
    <>
      {outcome === 'ok' && <span className="ag-burst">{Array.from({ length: 12 }, (_, i) => <i key={i} style={{ transform: `rotate(${i * 30}deg)` }}></i>)}</span>}
      <svg className={'ag-done ' + outcome} viewBox="0 0 120 120">
        <circle className="ring" cx="60" cy="60" r="46" pathLength={100} />
        <path className="mark" d={MARK[outcome]} pathLength={100} />
      </svg>
    </>
  );
}

export default function AgentScene({ agent, done = false, outcome = 'ok' }: { agent: AgentName; done?: boolean; outcome?: Outcome }) {
  const on = (k: AgentName) => !done && agent === k;
  return (
    <div className="ag-stage" data-agent={done ? 'done' : agent} aria-hidden="true">
      <div className={'ag-scene ag-manager' + (on('manager') ? ' on' : '')}><Manager /></div>
      <div className={'ag-scene ag-analysis' + (on('analysis') ? ' on' : '')}><Analysis /></div>
      <div className={'ag-scene ag-test' + (on('test') ? ' on' : '')}><Test /></div>
      <div className={'ag-scene ag-finish' + (done ? ' on' : '')}>{done && <Done outcome={outcome} />}</div>
    </div>
  );
}

/** The three agents as a row, the working one lit, with what it is doing. */
export function AgentStrip({ agent }: { agent: AgentName }) {
  return (
    <ol className="ag-strip" aria-label="Agents">
      {AGENTS.map(([key, name, doing]) => (
        <li key={key} className={'ag-pill ' + key + (agent === key ? ' on' : '')} aria-current={agent === key ? 'step' : undefined}>
          <i aria-hidden="true"></i>{name}{agent === key && <span>{doing}</span>}
        </li>
      ))}
    </ol>
  );
}
