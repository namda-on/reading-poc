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

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

export function ReadingSession({ topic, onFinish, onBack }: { topic: Topic; onFinish: () => void; onBack: () => void }) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [started, setStarted] = useState(false);
  const [index, setIndex] = useState(0);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(true); // 학습 시작 전에는 설정창을 열어둠

  const { visible, play } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const finishTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index]);

  useEffect(() => {
    if (!started) return; // 시작 버튼을 누르기 전까지 재생하지 않음(옵션 설정 시간 확보)
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current;
    const chunks = chunkSentence(script.english, s.unit, s.maxChunkWords);
    setCurrentChunks(chunks);
    play(
      chunks,
      { windowSize: s.windowSize, baseMsPerSyllable: s.baseMsPerSyllable, minDwellMs: MIN_DWELL_MS },
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
  }, [started, index, topic, play]);

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

      {!started ? (
        <div className="start-prompt">
          <p>준비되면 시작하세요.<br />설정(⚙)을 먼저 조절할 수 있어요.</p>
          <button
            className="start-btn"
            onClick={() => {
              setSettingsOpen(false);
              setStarted(true);
            }}
          >
            ▶ 시작
          </button>
        </div>
      ) : (
        <div className="chat">
          {topic.scripts.slice(0, index + 1).map((s, i) => {
            const info = speakerInfo(s.speaker);
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
      )}
    </div>
  );
}
