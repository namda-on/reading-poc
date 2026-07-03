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
const FADE_OUT_MS = 500; // 마지막 청크가 페이드아웃(CSS 450ms)된 뒤 문제로 넘어감

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
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [index, setIndex] = useState(0);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const { visible, play } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const finishTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index]);

  useEffect(() => {
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current;
    const chunks = chunkSentence(script.english, s.unit, s.maxChunkWords);
    setCurrentChunks(chunks);
    play(
      chunks,
      { windowSize: s.windowSize, baseMsPerWord: s.baseMsPerWord, minDwellMs: MIN_DWELL_MS },
      () => {
        // 마지막 스크립트면 페이드아웃을 기다렸다가 문제로, 아니면 다음 말풍선
        if (index + 1 >= topic.scripts.length) {
          finishTimer.current = window.setTimeout(() => onFinishRef.current(), FADE_OUT_MS);
          return;
        }
        gapTimer.current = window.setTimeout(() => setIndex((i) => i + 1), GAP_MS);
      },
    );
    return () => {
      if (gapTimer.current) window.clearTimeout(gapTimer.current);
      if (finishTimer.current) window.clearTimeout(finishTimer.current);
      gapTimer.current = null;
      finishTimer.current = null;
    };
  }, [index, topic, play]);

  const total = topic.scripts.length;
  const progressPct = Math.round(((index + 1) / total) * 100);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🏆</div>
          <div className="bar">
            <span className="bar-count">{index + 1}/{total}</span>
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
              visible={i === index ? visible : new Set<number>()}
            />
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
