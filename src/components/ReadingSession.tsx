import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence, type Chunk } from '../lib/chunk';
import { useSlidingReveal } from '../hooks/useSlidingReveal';
import { useSettings } from '../settings/SettingsContext';
import { DialogBubble } from './DialogBubble';
import './ReadingSession.css';

const MIN_DWELL_MS = 300;
const GAP_MS = 400;

export function ReadingSession({ topic, onFinish }: { topic: Topic; onFinish: () => void }) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const [index, setIndex] = useState(0);
  const [runId, setRunId] = useState(0); // 같은 index 재생 강제(리플레이)용
  const [finished, setFinished] = useState(false);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);

  const { visible, play, reset } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // 새 말풍선이 등장하거나 종료될 때 화면 하단으로 자동 스크롤
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index, runId, finished]);

  useEffect(() => {
    if (finished) return;
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current; // 시작 시점 설정 스냅샷
    const chunks = chunkSentence(script.english, s.unit);
    setCurrentChunks(chunks);
    play(
      chunks,
      { windowSize: s.windowSize, baseMsPerWord: s.baseMsPerWord, minDwellMs: MIN_DWELL_MS },
      () => {
        if (index + 1 >= topic.scripts.length) {
          setFinished(true);
          return;
        }
        gapTimer.current = window.setTimeout(() => setIndex((i) => i + 1), GAP_MS);
      },
    );
    return () => {
      if (gapTimer.current) {
        window.clearTimeout(gapTimer.current);
        gapTimer.current = null;
      }
    };
  }, [index, runId, finished, topic, play]);

  const replay = () => {
    if (gapTimer.current) {
      window.clearTimeout(gapTimer.current);
      gapTimer.current = null;
    }
    reset();
    setFinished(false);
    setIndex(0);
    setRunId((r) => r + 1); // index 가 이미 0이어도 effect 재실행
  };

  return (
    <div className="session">
      <div className="chat">
        {topic.scripts.slice(0, index + 1).map((s, i) => (
          <DialogBubble
            key={s.seq}
            speaker={s.speaker}
            chunks={i === index ? currentChunks : chunkSentence(s.english, settings.unit)}
            visible={i === index && !finished ? visible : new Set<number>()}
          />
        ))}
        <div ref={endRef} />
      </div>
      {finished && (
        <div className="session-actions">
          <button onClick={replay}>다시 보기</button>
          <button className="primary" onClick={onFinish}>문제 풀기</button>
        </div>
      )}
    </div>
  );
}
