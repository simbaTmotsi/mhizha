// Turn the captured material into a module the composition can import.
//
// Remotion bundles for a browser, so the composition cannot read files off disk. The two
// text files under docs/video/narration are the shared source of truth for BOTH renderers
// -- the Pillow one in scripts/video_render.py and this one -- and they are converted here
// rather than duplicated, so the two videos cannot disagree about what the machine did.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, "..", "..");
const read = (p) => readFileSync(join(repo, p), "utf8");

const beats = {};
for (const line of read("docs/video/narration/TIMINGS.txt").split("\n")) {
  if (!line.trim() || line.startsWith("#")) continue;
  const [start, end, beat, text] = line.split("\t");
  const n = Number(beat);
  beats[n] ??= { beat: n, start: Number(start), end: Number(end), cues: [] };
  beats[n].start = Math.min(beats[n].start, Number(start));
  beats[n].end = Math.max(beats[n].end, Number(end));
  beats[n].cues.push({ start: Number(start), end: Number(end), text });
}

const sessions = {};
let current = null;
for (const line of read("docs/video/narration/SESSIONS.txt").split("\n")) {
  if (line.startsWith("#")) continue;
  if (line.startsWith("\t")) { current?.raw.push(line.slice(1)); continue; }
  if (!line.trim()) continue;
  const [beat, wait, typed] = line.split("\t");
  current = { beat: Number(beat), wait: Number(wait), typed, raw: [] };
  sessions[current.beat] = current;
}

writeFileSync(join(here, "..", "src", "material.json"),
  JSON.stringify({ beats: Object.values(beats), sessions }, null, 2));
console.log(`material: ${Object.keys(beats).length} beats, ${Object.keys(sessions).length} sessions`);
