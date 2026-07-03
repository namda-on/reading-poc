import type { Chunk } from './chunk';

export interface RevealSettings {
  windowSize: number;
  baseMsPerWord: number;
  minDwellMs: number;
}

export interface RevealStep {
  index: number;
  showAt: number;
  hideAt: number;
}

export function dwellMs(chunk: Chunk, s: RevealSettings): number {
  const wordCount = chunk.text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(s.minDwellMs, wordCount * s.baseMsPerWord);
}

export function buildRevealSchedule(chunks: Chunk[], s: RevealSettings): { steps: RevealStep[]; totalMs: number } {
  const windowSize = Math.max(1, Math.floor(s.windowSize)); // 방어: 최소 1
  const showAt: number[] = [];
  let acc = 0;
  for (let i = 0; i < chunks.length; i++) {
    showAt.push(acc);
    acc += dwellMs(chunks[i], s);
  }
  const totalMs = acc;
  const steps: RevealStep[] = chunks.map((_, i) => {
    const hideIdx = i + windowSize; // 이 인덱스가 등장하면 i 는 꺼진다
    const hideAt = hideIdx < chunks.length ? showAt[hideIdx] : totalMs;
    return { index: i, showAt: showAt[i], hideAt };
  });
  return { steps, totalMs };
}
