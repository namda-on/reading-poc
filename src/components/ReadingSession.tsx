import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence, type Chunk } from '../lib/chunk';
import { useSlidingReveal } from '../hooks/useSlidingReveal';
import { useSettings } from '../settings/SettingsContext';
import { DialogBubble } from './DialogBubble';
import { SettingsPanel } from './SettingsPanel';
import './ReadingSession.css';

const MIN_DWELL_MS = 300;
const GAP_MS = 400;

// 이 코스에서 A는 항상 잡스, B는 대화 상대. 상대 이름은 괄호를 떼고 성(마지막 단어)만 한 줄로.
function speakerInfo(speaker: 'A' | 'B', partner: string) {
  if (speaker === 'A') return { name: '잡스', avatar: '🐻' };
  const base = partner.split('(')[0].trim();
  const parts = base.split(/\s+/);
  return { name: parts[parts.length - 1] || base, avatar: '🐰' };
}

export function ReadingSession({ topic, onFinish, onBack }: { topic: Topic; onFinish: () => void; onBack: () => void }) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const [index, setIndex] = useState(0);
  const [runId, setRunId] = useState(0); // 같은 index 재생 강제(리플레이)용
  const [finished, setFinished] = useState(false);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const { visible, play, reset } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index, runId, finished]);

  useEffect(() => {
    if (finished) return;
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current;
    const chunks = chunkSentence(script.english, s.unit, s.maxChunkWords);
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
    setRunId((r) => r + 1);
  };

  const total = topic.scripts.length;
  const progressPct = finished ? 100 : Math.round(((index + 1) / total) * 100);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🏆</div>
          <div className="bar">
            <span className="bar-count">{Math.min(index + 1, total)}/{total}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>
        <button className="icon-btn" onClick={() => setSettingsOpen((v) => !v)} aria-label="설정">⚙</button>
      </header>

      {settingsOpen && (
        <div className="settings-drop">
          <SettingsPanel />
        </div>
      )}

      <div className="chat">
        {topic.scripts.slice(0, index + 1).map((s, i) => {
          const info = speakerInfo(s.speaker, topic.partner);
          return (
            <DialogBubble
              key={s.seq}
              name={info.name}
              avatar={info.avatar}
              chunks={i === index ? currentChunks : chunkSentence(s.english, settings.unit, settings.maxChunkWords)}
              visible={i === index && !finished ? visible : new Set<number>()}
            />
          );
        })}
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
