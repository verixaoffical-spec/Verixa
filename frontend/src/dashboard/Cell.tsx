import { useLayoutEffect, useEffect, useRef, useState, type KeyboardEvent } from 'react';

interface Props {
  id: string;        // "kind|file|row|column", so Enter can find the same column in the next row
  value: string;
  onCommit: (value: string) => boolean;  // false when the edit was refused
  className?: string;
  label: string;
  maxLength: number;
  placeholder?: string;
  numeric?: boolean;
  readOnlyReason?: string;               // makes the cell read-only, with this as its tooltip
  multiline?: boolean;                   // T-096: long text wraps onto more lines instead of being cut off
}

const nextRowId = (id: string) => {
  const [kind, file, row, column] = id.split('|');
  return [kind, file, Number(row) + 1, column].join('|');
};

// A text cell that saves when you leave it. Enter moves down a row, Escape puts the old value back.
export default function Cell({ id, value, onCommit, className = '', label, maxLength, placeholder, numeric, readOnlyReason, multiline }: Props) {
  const [text, setText] = useState(value);
  const cancelled = useRef(false);
  const area = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {  // grow to fit the text (CSS field-sizing does this where supported; this covers the rest)
    const el = area.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight + 2}px`;
  }, [text]);

  useEffect(() => setText(value), [value]);  // the file changed, for example after Undo

  function onBlur() {
    if (cancelled.current) { cancelled.current = false; return; }
    if (text === value) return;
    if (onCommit(text)) setText(text.trim());
    else setText(value);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing || e.ctrlKey || e.metaKey) return;
    if (e.key === 'Escape') {
      cancelled.current = true;
      setText(value);
      e.currentTarget.blur();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const next = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[data-cell="${CSS.escape(nextRowId(id))}"]`);
      if (next) { next.focus(); next.select(); } else e.currentTarget.blur();
    }
  }

  if (multiline) {  // Enter still moves down a row, so a name never gets a line break typed into it
    return (
      <textarea ref={area} rows={1} className={'cell wrap ' + className} data-cell={id} value={text} maxLength={maxLength}
                placeholder={placeholder} aria-label={label} readOnly={!!readOnlyReason} title={readOnlyReason}
                onChange={e => setText(e.target.value.replace(/[\r\n]+/g, ' '))} onBlur={onBlur} onKeyDown={onKeyDown} />
    );
  }
  return (
    <input className={'cell ' + className} data-cell={id} value={text} maxLength={maxLength} placeholder={placeholder}
           aria-label={label} inputMode={numeric ? 'numeric' : undefined}
           readOnly={!!readOnlyReason} title={readOnlyReason}
           onChange={e => setText(e.target.value)} onBlur={onBlur} onKeyDown={onKeyDown} />
  );
}
