import { describe, it, expect } from 'vitest';
import { buildRevealSchedule, dwellMs } from './reveal';
import type { Chunk } from './chunk';

const ch = (text: string): Chunk => ({ text, start: 0, end: text.length });
const S = { windowSize: 1, baseMsPerSyllable: 100, minDwellMs: 300 };

describe('dwellMs', () => {
  it('음절 수 × 기본속도, 최소값 보장', () => {
    expect(dwellMs(ch('to Rome'), S)).toBe(300); // 2음절*100=200 < 300 → 300
    expect(dwellMs(ch('one two three four'), S)).toBe(400); // 4음절*100=400
  });
});

describe('buildRevealSchedule', () => {
  it('showAt 은 앞 청크 dwell 누적', () => {
    const chunks = [ch('a'), ch('b'), ch('c')]; // 각 dwell 300
    const { steps, totalMs } = buildRevealSchedule(chunks, S);
    expect(steps.map((s) => s.showAt)).toEqual([0, 300, 600]);
    expect(totalMs).toBe(900);
  });
  it('windowSize=1 이면 다음 청크 등장 시 이전 청크 꺼짐', () => {
    const chunks = [ch('a'), ch('b'), ch('c')];
    const { steps } = buildRevealSchedule(chunks, S);
    expect(steps[0].hideAt).toBe(300); // b 등장 시 a off
    expect(steps[2].hideAt).toBe(900); // 마지막은 totalMs 에 off
  });
  it('windowSize=2 이면 두 청크 뒤에 꺼짐', () => {
    const chunks = [ch('a'), ch('b'), ch('c')];
    const { steps } = buildRevealSchedule(chunks, { ...S, windowSize: 2 });
    expect(steps[0].hideAt).toBe(600); // c(index2) 등장 시 a off
  });
  it('마지막 창의 청크들은 동시에 사라지지 않고 하나씩 빠진다(drain)', () => {
    const chunks = [ch('a'), ch('b'), ch('c'), ch('d'), ch('e')]; // dwell 300, shownMs 1500, drainStep 160
    const { steps, totalMs } = buildRevealSchedule(chunks, { ...S, windowSize: 2 });
    const hides = steps.map((s) => s.hideAt);
    expect(hides).toEqual([600, 900, 1200, 1500, 1660]); // 앞은 등장 리듬(300), 꼬리는 drain(160)
    expect(new Set(hides).size).toBe(hides.length); // 전부 다른 시각(동시 소멸 없음)
    expect(totalMs).toBe(1660);
  });
  it('hideOld=false 면 창 크기와 무관하게 문장 끝까지 유지', () => {
    const chunks = [ch('a'), ch('b'), ch('c')];
    const { steps, totalMs } = buildRevealSchedule(chunks, { ...S, hideOld: false });
    expect(steps.map((s) => s.hideAt)).toEqual([totalMs, totalMs, totalMs]);
  });
});
