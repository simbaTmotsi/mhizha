// The terminal beats are real captures, so they arrive with the SGR codes rich emitted.
// Only the codes it actually uses are handled; anything else resets, which is the safe
// direction for a renderer that must not invent colour.
export type Span = {text: string; colour: string; bold: boolean; dim: boolean};

export const COLOURS = {
  fg: '#dee2e9',
  dim: '#787e8a',
  prompt: '#7ec8a0',
  yellow: '#d6b260',
  cyan: '#78bed6',
  bg: '#12141a',
};

const COLUMNS = 88;

// A terminal emulator wraps at its width. This renderer lays out, so without this the
// BLOCKED line in beat 7, about two hundred characters and the strongest thing in the
// video, runs off the frame.
const wrap = (spans: Span[]): Span[][] => {
  const rows: Span[][] = [];
  let row: Span[] = [];
  let used = 0;
  for (const span of spans) {
    let text = span.text;
    while (text) {
      const room = COLUMNS - used;
      if (text.length <= room) {
        row.push({...span, text});
        used += text.length;
        break;
      }
      let cut = text.lastIndexOf(' ', room);
      if (cut <= 0) cut = room;
      row.push({...span, text: text.slice(0, cut)});
      text = text.slice(cut).replace(/^ +/, '');
      rows.push(row);
      row = [];
      used = 0;
    }
  }
  rows.push(row);
  return rows.length ? rows : [[]];
};

export const parse = (raw: string[]): Span[][] => {
  let colour = COLOURS.fg;
  let bold = false;
  let dim = false;
  const lines: Span[][] = [];
  for (const rawLine of raw) {
    const spans: Span[] = [];
    for (const part of rawLine.split(/(\x1b\[[0-9;]*m)/)) {
      if (!part) continue;
      const code = /^\x1b\[([0-9;]*)m$/.exec(part);
      if (code) {
        for (const c of (code[1] || '0').split(';')) {
          if (c === '' || c === '0') {
            colour = COLOURS.fg;
            bold = false;
            dim = false;
          } else if (c === '1') bold = true;
          else if (c === '2') dim = true;
          else if (c === '33') colour = COLOURS.yellow;
          else if (c === '36') colour = COLOURS.cyan;
        }
        continue;
      }
      spans.push({text: part, colour, bold, dim});
    }
    lines.push(spans);
  }
  while (lines.length && !lines[lines.length - 1].some((s) => s.text.trim())) lines.pop();
  return lines.flatMap(wrap);
};
