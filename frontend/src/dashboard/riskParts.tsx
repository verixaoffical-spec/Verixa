/* Pieces of the Risk screens shared by the Overview table and the Pull Requests section (T-096 moved them here
 * from RiskView.tsx unchanged, so both lists show a pull request the same way). */
import type { Assessment, RiskLabel } from './api';
import { Chip } from './connection';
import { History } from './RiskCharts';

export type Tab = 'prs' | 'overview' | 'graph' | 'live';

// The mock-up used low / med / high as class names. Map the agent's labels onto them.
export const BADGE: Record<RiskLabel, string> = { Low: 'low', Medium: 'med', High: 'high' };
export const STATE_TEXT: Record<Assessment['state'], string> = {
  queued: 'Queued',
  running: 'Analysing',
  scored: 'Scored',
  needs_human_review: 'Needs review',
  failed: 'Failed',
};
export const initials = (who: string | null) =>
  (who || '??').replace(/[^a-zA-Z0-9]/g, '').slice(0, 2).toUpperCase() || '??';

// A stable colour per author, so the same person keeps the same avatar between loads
export function hue(who: string | null): number {
  let h = 0;
  for (const ch of who || 'anon') h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

export function ago(iso: string | null): string {
  if (!iso) return '';
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (!isFinite(seconds) || seconds < 0) return '';
  if (seconds < 60) return 'just now';
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function RiskBadge({ label }: { label: RiskLabel | null }) {
  if (!label) return <span className="rbadge none"><i></i>Not scored</span>;
  return <span className={'rbadge ' + BADGE[label]}><i></i>{label}</span>;
}

export function StateBadge({ state }: { state: Assessment['state'] }) {
  const busy = state === 'queued' || state === 'running';
  return (
    <span className={'rstate ' + state}>
      {busy && <i></i>}
      {state === 'scored' && <svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>}
      {STATE_TEXT[state]}
    </span>
  );
}

export function Detail({ row, history, onGo }: { row: Assessment; history: Assessment[]; onGo: (tab: Tab) => void }) {
  const raised = row.base_label && row.risk_label && row.base_label !== row.risk_label;
  return (
    <tr>
      <td className="rdetail" colSpan={5}>
        <div className="rdetail-in">
          {!!row.errors.length && (
            <div className="rerr">
              <b>{row.state === 'failed' ? 'The analysis could not finish' : 'The Manager did not accept the output'}</b>
              {row.errors.join(' · ')}
              {row.attempts > 0 && ` (after ${row.attempts} attempt${row.attempts === 1 ? '' : 's'})`}
            </div>
          )}

          {!!row.risk_factors.length && (
            <div>
              <h4>Why this label</h4>
              <ul className="rfactors">
                {row.risk_factors.map((factor, i) => <li key={i}>{factor}</li>)}
              </ul>
            </div>
          )}

          {row.reasoning && (
            <div>
              <h4>Agent reasoning</h4>
              <p className="rreason">{row.reasoning}</p>
            </div>
          )}

          {row.concern && (
            <div className="rconcern" role="note">
              <h4>The agent questions this label</h4>
              <p>{row.concern}</p>
              <p className="rconcern-note">The label comes from the rules and has not been changed. Check this before relying on it.</p>
            </div>
          )}

          {!!row.test_areas.length && (
            <div>
              <h4>Suggested test areas</h4>
              <ul className="rareas">
                {row.test_areas.map((area, i) => <li key={i}><span>{i + 1}</span>{area}</li>)}
              </ul>
            </div>
          )}

          <History rows={history} />

          <div className="rmeta">
            {row.module && <Chip on={false}>module {row.module}</Chip>}
            {row.files_changed !== null && (
              <Chip on={false}>{row.files_changed} file{row.files_changed === 1 ? '' : 's'}, {row.lines_changed ?? 0} lines</Chip>
            )}
            {row.past_defects !== null && <Chip on={false}>{row.past_defects} past fix{row.past_defects === 1 ? '' : 'es'} here</Chip>}
            {row.sensitivity && <Chip on={false}>sensitivity {row.sensitivity}</Chip>}
            {raised && <Chip on={false}>raised from {row.base_label} by a minimum label</Chip>}
            {row.model_used && <Chip on={false}>explained by {row.model_used}</Chip>}
            {row.attempts > 1 && <Chip on={false}>{row.attempts} manager attempts</Chip>}
            <button className="btn ghost sm" onClick={() => onGo('graph')}>Open dependency graph</button>
            <button className="btn ghost sm" onClick={() => onGo('live')}>Open run log</button>
            {row.pr_url?.startsWith('https://github.com/') && (
              <a className="btn ghost sm" href={row.pr_url} target="_blank" rel="noopener noreferrer">
                Open on GitHub
              </a>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
}

