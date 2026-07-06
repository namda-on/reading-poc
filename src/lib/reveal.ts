import { syllable } from 'syllable';
import type { Chunk } from './chunk';

export interface RevealSettings {
  windowSize: number;
  baseMsPerSyllable: number;
  minDwellMs: number;
  // 오래된 청크 숨기기. false 면 문장 끝까지 누적(창 크기 무시). 미지정=켜짐.
  hideOld?: boolean;
  // 문장 끝 마지막 창이 하나씩 빠지는 간격(ms). 작을수록 빨리 사라짐.
  drainStepMs?: number;
}

// 문장 끝에서 마지막 창이 하나씩 빠질 때의 간격(ms) 기본값(설정 미지정 시).
const DEFAULT_DRAIN_STEP_MS = 160;

export interface RevealStep {
  index: number;
  showAt: number;
  hideAt: number;
}

export function dwellMs(chunk: Chunk, s: RevealSettings): number {
  // 단어 수가 아니라 음절 수에 비례. 최소 1음절 보장.
  const syllables = Math.max(1, syllable(chunk.text));
  return Math.max(s.minDwellMs, syllables * s.baseMsPerSyllable);
}

export function buildRevealSchedule(chunks: Chunk[], s: RevealSettings): { steps: RevealStep[]; totalMs: number } {
  const windowSize = Math.max(1, Math.floor(s.windowSize)); // 방어: 최소 1
  const showAt: number[] = [];
  let acc = 0;
  for (let i = 0; i < chunks.length; i++) {
    showAt.push(acc);
    acc += dwellMs(chunks[i], s);
  }
  const shownMs = acc; // 모든 청크가 등장 완료되는 시각
  const hideOld = s.hideOld !== false; // 미지정=켜짐

  if (!hideOld) {
    // 숨기기 off: 문장 끝까지 누적.
    const steps = chunks.map((_, i) => ({ index: i, showAt: showAt[i], hideAt: shownMs }));
    return { steps, totalMs: shownMs };
  }

  // 청크 i 는 i+N 이 등장할 때 사라진다. 마지막 N개는 등장할 다음 청크가 없으므로, 등장이 끝난
  // 뒤에도 하나씩(DRAIN_STEP_MS 간격) 빠지도록 스케줄을 이어붙인다 — 통째로 동시에 사라지는 것 방지.
  const avg = chunks.length > 0 ? shownMs / chunks.length : 0;
  const drainStep = Math.min(avg, s.drainStepMs ?? DEFAULT_DRAIN_STEP_MS);
  const showAtExt = (idx: number) => (idx < chunks.length ? showAt[idx] : shownMs + (idx - chunks.length) * drainStep);
  const steps: RevealStep[] = chunks.map((_, i) => ({ index: i, showAt: showAt[i], hideAt: showAtExt(i + windowSize) }));
  const totalMs = shownMs + Math.max(0, windowSize - 1) * drainStep; // 마지막 청크가 빠질 때까지
  return { steps, totalMs };
}
