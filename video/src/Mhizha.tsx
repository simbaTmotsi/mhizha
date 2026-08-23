import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig, useCurrentFrame, interpolate} from 'remotion';
import material from './material.json';
import {parse, COLOURS} from './ansi';
import {TerminalBeat, Shell, Prompt} from './Terminal';
import {Card} from './Cards';
import {Pipeline} from './Pipeline';

// Same numbers as the Pillow renderer, and for the same reasons. The typing rate is a
// person, not the machine; the waits come from the capture and are never touched.
const TYPING_CPS = 14;
const FADE = 0.45;
const BEAT6_SPLIT = 95.0;
const CLOSING_SECONDS = 4.0;
const GAP_BETWEEN_BEATS = 0.35;

const beats = material.beats as {beat: number; start: number; end: number}[];
const sessions = material.sessions as Record<
  string,
  {beat: number; wait: number; typed: string; raw: string[]}
>;
const window = (n: number) => beats.find((b) => b.beat === n)!;
export const NARRATION_END = Math.max(...beats.map((b) => b.end));
export const TOTAL = NARRATION_END + GAP_BETWEEN_BEATS + CLOSING_SECONDS;

/** A dissolve on the way in. Beats are separate scenes, so they cross rather than cut. */
const Dissolve: React.FC<{seconds?: number; children: React.ReactNode}> = ({
  seconds = FADE,
  children,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = interpolate(frame / fps, [0, seconds], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>;
};

const at = (seconds: number, fps: number) => Math.round(seconds * fps);

const Beat: React.FC<{n: number; sweepFrom?: number; from?: number; to?: number}> = ({
  n,
  sweepFrom,
  from,
  to,
}) => {
  const {fps} = useVideoConfig();
  const w = window(n);
  const start = from ?? w.start;
  const end = to ?? w.end;
  // Beat 3 has no session of its own: it holds beat 2's answer and lifts the sources
  // table out of it, which is what the beat sheet asks for.
  const s = sessions[String(n)];
  const lines = s ? parse(s.raw) : [];
  const answer = parse(sessions['2'].raw);
  const table = answer.findIndex((row) => row.some((sp) => sp.text.includes('Based on')));

  return (
    <Sequence from={at(start, fps)} durationInFrames={at(end - start, fps)}>
      <Dissolve>
        {n === 3 ? (
          <TerminalBeat
            typed={sessions['2'].typed}
            wait={0}
            lines={answer}
            cps={1e6}
            highlight={table >= 0 ? [table, answer.length - 1] : null}
            sweepFrom={sweepFrom}
          />
        ) : (
          <TerminalBeat typed={s.typed} wait={s.wait} lines={lines} cps={TYPING_CPS} />
        )}
      </Dissolve>
    </Sequence>
  );
};

export const Mhizha: React.FC = () => {
  const {fps} = useVideoConfig();
  const one = window(1);
  const six = window(6);

  return (
    <AbsoluteFill style={{background: COLOURS.bg}}>
      <Sequence durationInFrames={at(one.end - 2.6, fps)}>
        <Dissolve seconds={1.1}>
          <Card
            title="Mhizha"
            lines={[
              'An offline agronomy assistant for smallholder farmers in Zimbabwe.',
              'It cites what it used, and refuses what it cannot source.',
            ]}
            footnote="ADTC 2026 · Laptop LLM track · domain: agriculture"
          />
        </Dissolve>
      </Sequence>

      <Sequence from={at(one.end - 2.6, fps)} durationInFrames={at(2.6 + 0.35, fps)}>
        <Dissolve>
          <Shell>
            <Prompt typed="" cursor />
          </Shell>
        </Dissolve>
      </Sequence>

      <Beat n={2} />
      <Beat n={3} sweepFrom={1.1} />
      <Beat n={4} />
      <Beat n={5} />

      <Sequence from={at(six.start, fps)} durationInFrames={at(BEAT6_SPLIT - six.start, fps)}>
        <Dissolve>
          <Pipeline dimAt={3.4} liftAt={2.6} />
        </Dissolve>
      </Sequence>
      <Beat n={6} from={BEAT6_SPLIT} />

      <Beat n={7} />

      <Sequence from={at(NARRATION_END + GAP_BETWEEN_BEATS, fps)}>
        <Dissolve seconds={0.9}>
          <Card
            title="Mhizha"
            lines={['Simbarashe Timothy Motsi', 'team_id  mhizha', 'github.com/simbaTmotsi/mhizha']}
            footnote="Narration: Kokoro-82M, a synthetic voice."
          />
        </Dissolve>
      </Sequence>
    </AbsoluteFill>
  );
};
