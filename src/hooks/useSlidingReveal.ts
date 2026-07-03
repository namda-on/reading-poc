import { useCallback, useEffect, useRef, useState } from 'react';
import { buildRevealSchedule, type RevealSettings } from '../lib/reveal';
import type { Chunk } from '../lib/chunk';

export function useSlidingReveal() {
  const [visible, setVisible] = useState<Set<number>>(new Set());
  const timers = useRef<number[]>([]);
  const gen = useRef(0);

  const clear = useCallback(() => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }, []);

  const play = useCallback(
    (chunks: Chunk[], settings: RevealSettings, onDone?: () => void) => {
      clear();
      const myGen = ++gen.current;
      setVisible(new Set());
      const { steps, totalMs } = buildRevealSchedule(chunks, settings);
      for (const step of steps) {
        timers.current.push(
          window.setTimeout(() => {
            if (gen.current !== myGen) return;
            setVisible((prev) => new Set(prev).add(step.index));
          }, step.showAt),
        );
        timers.current.push(
          window.setTimeout(() => {
            if (gen.current !== myGen) return;
            setVisible((prev) => {
              const n = new Set(prev);
              n.delete(step.index);
              return n;
            });
          }, step.hideAt),
        );
      }
      timers.current.push(
        window.setTimeout(() => {
          if (gen.current !== myGen) return;
          onDone?.();
        }, totalMs + 50),
      );
    },
    [clear],
  );

  const reset = useCallback(() => {
    gen.current++;
    clear();
    setVisible(new Set());
  }, [clear]);

  useEffect(() => clear, [clear]); // 언마운트 시 타이머 정리
  return { visible, play, reset };
}
