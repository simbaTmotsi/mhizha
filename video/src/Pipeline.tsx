import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {COLOURS} from './ansi';

const TEXT = '"SF Pro Text", -apple-system, "Helvetica Neue", sans-serif';
const MONO = 'Menlo, "SF Mono", Monaco, monospace';

const STACK: [string, string][] = [
  ['i18n', 'detect en / sn / nd'],
  ['embedder', 'all-MiniLM-L6-v2, on device'],
  ['retrieve', 'top-k from one sqlite file'],
  ['confidence', 'below threshold, do not generate'],
  ['prompt', 'retrieved passages only'],
  ['safety', 'citations, dose gate, abstention'],
];

/**
 * The stack, and the one part of it the competition actually profiles.
 *
 * This is the beat where motion carries meaning rather than decorating: the stack builds
 * while the narration describes it, then dims on "none of this code runs while judges are
 * scoring" as the model file below it lights up. A static diagram can state that. It
 * cannot show it happening.
 */
export const Pipeline: React.FC<{dimAt: number; liftAt: number}> = ({dimAt, liftAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const dim = interpolate(t, [dimAt, dimAt + 0.8], [1, 0.3], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const lift = spring({frame: frame - liftAt * fps, fps, config: {damping: 200, mass: 0.7}});

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: COLOURS.bg,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: TEXT,
        WebkitFontSmoothing: 'antialiased',
      }}
    >
      <div style={{opacity: dim, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{fontSize: 24, color: COLOURS.dim, marginBottom: 12}}>farmer question</div>
        <div style={{width: 1, height: 26, background: COLOURS.dim}} />
        <div
          style={{
            border: `1px solid ${COLOURS.dim}`,
            borderRadius: 10,
            padding: '22px 34px',
            display: 'grid',
            gridTemplateColumns: 'auto auto',
            columnGap: 34,
            rowGap: 12,
          }}
        >
          {STACK.map(([name, detail], index) => {
            const s = spring({
              frame: frame - index * 3,
              fps,
              config: {damping: 200, mass: 0.5},
            });
            return (
              <React.Fragment key={name}>
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 23,
                    color: COLOURS.fg,
                    opacity: s,
                    transform: `translateY(${interpolate(s, [0, 1], [8, 0])}px)`,
                  }}
                >
                  {name}
                </div>
                <div
                  style={{
                    fontSize: 23,
                    color: COLOURS.fg,
                    opacity: s * 0.78,
                    transform: `translateY(${interpolate(s, [0, 1], [8, 0])}px)`,
                  }}
                >
                  {detail}
                </div>
              </React.Fragment>
            );
          })}
        </div>
        <div style={{width: 1, height: 26, background: COLOURS.dim}} />
      </div>

      <div
        style={{
          border: `1px solid ${COLOURS.yellow}`,
          borderRadius: 10,
          padding: '18px 40px',
          textAlign: 'center',
          opacity: lift,
          transform: `scale(${interpolate(lift, [0, 1], [0.94, 1])})`,
          boxShadow: `0 0 ${interpolate(lift, [0, 1], [0, 44])}px rgba(214,178,96,0.14)`,
        }}
      >
        <div style={{fontFamily: MONO, fontSize: 26, fontWeight: 700, color: COLOURS.yellow}}>
          the model file
        </div>
        <div style={{fontFamily: MONO, fontSize: 23, color: COLOURS.yellow, opacity: 0.85, marginTop: 6}}>
          Qwen3.5 2B &nbsp; Q4_K_M &nbsp; GGUF
        </div>
      </div>

      <div style={{marginTop: 46, textAlign: 'center', opacity: lift}}>
        <div style={{fontSize: 26, color: COLOURS.fg}}>
          the competition profiles the model file, and only the model file.
        </div>
        <div style={{fontSize: 26, color: COLOURS.dim, marginTop: 8}}>
          everything above it is ours, and none of it runs while judges score.
        </div>
      </div>
    </div>
  );
};
