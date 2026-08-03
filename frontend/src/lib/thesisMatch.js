// Locate the sentence(s) in the learner's draft that Compass currently recognizes
// as the thesis, so the UI can highlight them in place. current_thesis from the
// engine is a "close paraphrase in the learner's own words", so an exact substring
// match may fail; we fall back to sentence-level token overlap. Returns an array of
// [start, end] character ranges into the original draft (never mutates the text).

const norm = (s) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

function mergeRanges(ranges) {
  if (ranges.length <= 1) return ranges;
  const sorted = [...ranges].sort((a, b) => a[0] - b[0]);
  const out = [sorted[0]];
  for (let i = 1; i < sorted.length; i++) {
    const last = out[out.length - 1];
    if (sorted[i][0] <= last[1]) last[1] = Math.max(last[1], sorted[i][1]);
    else out.push(sorted[i]);
  }
  return out;
}

export function findThesisRanges(draft, thesis) {
  if (!draft || !thesis) return [];

  // 1) Direct (case-insensitive) substring of the quoted thesis.
  const stripped = thesis.trim().replace(/^["'“”‘’]+|["'“”‘’]+$/g, "").trim();
  if (stripped) {
    const idx = draft.toLowerCase().indexOf(stripped.toLowerCase());
    if (idx >= 0) return [[idx, idx + stripped.length]];
  }

  // 2) Sentence-level token overlap against the thesis' content words.
  const thesisTokens = new Set(norm(thesis).split(" ").filter((w) => w.length >= 4));
  if (thesisTokens.size < 2) return [];

  const ranges = [];
  const sentenceRe = /[^.!?]+[.!?]*/g;
  let m;
  while ((m = sentenceRe.exec(draft)) !== null) {
    const sent = m[0];
    if (!sent.trim()) continue;
    const start = m.index;
    const end = start + sent.length;
    const sentTokens = norm(sent).split(" ").filter((w) => w.length >= 4);
    if (sentTokens.length === 0) continue;
    const seen = new Set();
    let common = 0;
    for (const w of sentTokens) {
      if (thesisTokens.has(w) && !seen.has(w)) {
        common++;
        seen.add(w);
      }
    }
    if (common / thesisTokens.size >= 0.5) {
      const lead = sent.length - sent.trimStart().length;
      const trail = sent.length - sent.trimEnd().length;
      ranges.push([start + lead, end - trail]);
    }
  }
  return mergeRanges(ranges);
}

// Expand each [start,end] outward to FULL sentence boundaries so a shaded communicative
// unit never splits a sentence (Visible Interpretation rule 4). Sentence terminators are
// . ! ? plus any trailing closing quotes/brackets; leading/trailing whitespace is trimmed.
export function snapRangesToSentences(draft, ranges) {
  if (!draft || !ranges || !ranges.length) return ranges || [];
  const n = draft.length;
  const isTerm = (ch) => ch === "." || ch === "!" || ch === "?";
  const closers = "\"'”’)]";
  const out = ranges.map(([s0, e0]) => {
    const s = Math.max(0, Math.min(s0, n));
    const e = Math.max(0, Math.min(e0, n));
    // expand start LEFT to just after the previous sentence terminator
    let i = s - 1;
    while (i >= 0 && !isTerm(draft[i])) i--;
    let start = i + 1;
    // expand end RIGHT through the terminator that ends this sentence (+ closing marks)
    let j = Math.max(e - 1, start);
    while (j < n && !isTerm(draft[j])) j++;
    while (j < n && (isTerm(draft[j]) || closers.includes(draft[j]))) j++;
    let end = Math.min(n, j);
    // trim surrounding whitespace so shading hugs the text
    while (start < end && /\s/.test(draft[start])) start++;
    while (end > start && /\s/.test(draft[end - 1])) end--;
    return [start, end];
  });
  return mergeRanges(out);
}

// Remove any part of `ranges` that overlaps a `blockers` range (e.g. keep the
// Elaboration span from overlapping the Thesis span). Returns clipped [start,end]s.
export function subtractRanges(ranges, blockers) {
  if (!ranges || !ranges.length || !blockers || !blockers.length) return ranges || [];
  let out = [...ranges];
  for (const [bs, be] of blockers) {
    const next = [];
    for (const [s, e] of out) {
      if (e <= bs || s >= be) { next.push([s, e]); continue; } // no overlap
      if (s < bs) next.push([s, bs]);   // keep the part before the blocker
      if (e > be) next.push([be, e]);   // keep the part after the blocker
    }
    out = next;
  }
  return out.filter(([s, e]) => e > s);
}
