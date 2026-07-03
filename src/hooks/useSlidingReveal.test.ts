// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSlidingReveal } from './useSlidingReveal';
import type { Chunk } from '../lib/chunk';

const ch = (t: string): Chunk => ({ text: t, start: 0, end: t.length });
const S = { windowSize: 1, baseMsPerSyllable: 100, minDwellMs: 300 };

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('useSlidingReveal', () => {
  it('스케줄대로 노출·소멸하고 onDone 호출', () => {
    const onDone = vi.fn();
    const { result } = renderHook(() => useSlidingReveal());
    act(() => result.current.play([ch('a'), ch('b')], S, onDone));
    act(() => void vi.advanceTimersByTime(0));
    expect([...result.current.visible]).toEqual([0]); // a 노출
    act(() => void vi.advanceTimersByTime(300));
    expect([...result.current.visible]).toEqual([1]); // b 노출, a 소멸(window=1)
    act(() => void vi.advanceTimersByTime(400));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('reset 후 옛 타이머는 visible 을 건드리지 않는다 (generation guard)', () => {
    const { result } = renderHook(() => useSlidingReveal());
    act(() => result.current.play([ch('a'), ch('b')], S));
    act(() => result.current.reset());
    act(() => void vi.advanceTimersByTime(1000));
    expect([...result.current.visible]).toEqual([]);
  });
});
