import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {COLOURS, Span} from './ansi';

const MONO = 'Menlo, "SF Mono", Monaco, monospace';
export const FONT_SIZE = 24;
export const LINE_HEIGHT = 30;

export const Line: React.FC<{spans: Span[]; faded?: boolean}> = ({spans, faded}) => (
  <div style={{height: LINE_HEIGHT, whiteSpace: 'pre', opacity: faded ? 0.26 : 1}}>
    {spans.map((s, i) => (
      <span
        key={i}
        style={{
          color: s.colour,
          fontWeight: s.bold ? 700 : 400,
          opacity: s.dim ? 0.58 : 1,
        }}
      >
        {s.text}
      </span>
    ))}
  </div>
);

/** A block cursor that blinks the way a real one does, on the frame clock. */
export const Cursor: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const on = Math.floor((frame / fps) * 2) % 2 === 0;
  return (
    <span
      style={{
        display: 'inline-block',
        width: '1ch',
        height: FONT_SIZE + 2,
        verticalAlign: 'text-bottom',
        background: COLOURS.fg,
        opacity: on ? 1 : 0,
      }}
    />
  );
};

export const Shell: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      background: COLOURS.bg,
      fontFamily: MONO,
      fontSize: FONT_SIZE,
      lineHeight: `${LINE_HEIGHT}px`,
      color: COLOURS.fg,
      padding: '54px 96px',
      fontVariantLigatures: 'none',
      WebkitFontSmoothing: 'antialiased',
    }}
  >
    {children}
  </div>
);

export const Prompt: React.FC<{typed: string; cursor?: boolean}> = ({typed, cursor}) => (
  <div style={{height: LINE_HEIGHT, whiteSpace: 'pre'}}>
    <span style={{color: COLOURS.prompt, fontWeight: 700}}>$ </span>
    <span>{typed}</span>
    {cursor ? <Cursor /> : null}
  </div>
);

/**
 * A terminal beat: the command typed, the wait the machine actually took, the output.
 *
 * `wait` is measured, not chosen. Nothing here is sped up; the pause is the pause.
 */
export const TerminalBeat: React.FC<{
  typed: string;
  wait: number;
  lines: Span[][];
  cps: number;
  highlight?: [number, number] | null;
  sweepFrom?: number;
}> = ({typed, wait, lines, cps, highlight, sweepFrom}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const typingDone = typed.length / cps;
  const shown = Math.min(typed.length, Math.floor(t * cps));
  const out = t >= typingDone + wait;

  // Beat 3 lifts the sources table out of an answer already on screen. A sweep reads as
  // attention moving; a hard dim reads as a second screenshot.
  const sweep =
    sweepFrom === undefined
      ? 1
      : interpolate(t, [sweepFrom, sweepFrom + 0.9], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

  return (
    <Shell>
      <Prompt typed={typed.slice(0, shown)} cursor={!out} />
      {out ? <div style={{height: LINE_HEIGHT}} /> : null}
      {out
        ? lines.map((spans, index) => {
            const inside =
              highlight && index >= highlight[0] && index <= highlight[1];
            const faded = highlight ? !inside : false;
            return (
              <div
                key={index}
                style={{opacity: faded ? 1 - 0.74 * sweep : 1}}
              >
                <Line spans={spans} />
              </div>
            );
          })
        : null}
    </Shell>
  );
};
