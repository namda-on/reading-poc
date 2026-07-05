import { syllable } from 'syllable';
import type { Chunk } from './chunk';

export interface RevealSettings {
  windowSize: number;
  baseMsPerSyllable: number;
  minDwellMs: number;
  // 오래된 청크 숨기기. false 면 문장 끝까지 누적(창 크기 무시). 미지정=켜짐.
  hideOld?: boolean;
}

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
  const totalMs = acc;
  const hideOld = s.hideOld !== false; // 미지정=켜짐
  const steps: RevealStep[] = chunks.map((_, i) => {
    const hideIdx = i + windowSize; // 이 인덱스가 등장하면 i 는 꺼진다
    // 숨기기 off: 문장 끝(totalMs)까지 계속 보인다.
    const hideAt = hideOld && hideIdx < chunks.length ? showAt[hideIdx] : totalMs;
    return { index: i, showAt: showAt[i], hideAt };
  });
  return { steps, totalMs };
}
