import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {COLOURS} from './ansi';

// The terminal beats stay monospace because a terminal is. Everything that is not a
// terminal gets a real typeface, which is most of what this renderer buys over the other
// one: the Pillow build draws every card at a fixed monospace advance.
const DISPLAY = '"SF Pro Display", -apple-system, "Helvetica Neue", sans-serif';
const TEXT = '"SF Pro Text", -apple-system, "Helvetica Neue", sans-serif';

const Rise: React.FC<{delay: number; children: React.ReactNode}> = ({delay, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200, mass: 0.6}});
  return (
    <div style={{opacity: s, transform: `translateY(${interpolate(s, [0, 1], [14, 0])}px)`}}>
      {children}
    </div>
  );
};

export const Card: React.FC<{
  title: string;
  lines: string[];
  footnote?: string;
}> = ({title, lines, footnote}) => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      background: COLOURS.bg,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      WebkitFontSmoothing: 'antialiased',
    }}
  >
    <Rise delay={0}>
      <div
        style={{
          fontFamily: DISPLAY,
          fontSize: 74,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          color: COLOURS.fg,
        }}
      >
        {title}
      </div>
    </Rise>
    <Rise delay={5}>
      <div style={{width: 148, height: 1, background: COLOURS.dim, margin: '26px auto 30px'}} />
    </Rise>
    {lines.map((line, index) => (
      <Rise key={index} delay={8 + index * 4}>
        <div
          style={{
            fontFamily: TEXT,
            fontSize: 29,
            lineHeight: '46px',
            color: COLOURS.fg,
            opacity: 0.92,
          }}
        >
          {line}
        </div>
      </Rise>
    ))}
    {footnote ? (
      <Rise delay={8 + lines.length * 4 + 4}>
        <div
          style={{
            fontFamily: TEXT,
            fontSize: 22,
            letterSpacing: '0.04em',
            color: COLOURS.dim,
            marginTop: 44,
          }}
        >
          {footnote}
        </div>
      </Rise>
    ) : null}
  </div>
);
