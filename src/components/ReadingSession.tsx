import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence, type Chunk } from '../lib/chunk';
import { useSlidingReveal } from '../hooks/useSlidingReveal';
import { useSettings } from '../settings/SettingsContext';
import { DialogBubble } from './DialogBubble';
import { SettingsPanel } from './SettingsPanel';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';

const MIN_DWELL_MS = 300;
const GAP_MS = 400;
const FADE_OUT_MS = 500; // 마지막 청크가 페이드아웃(CSS 450ms)된 뒤 문제로 넘어감
const READY_MS = 800; // 시작 전 준비 신호(첫 텍스트 자리에 dot 깜빡임)

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

export function ReadingSession({ topic, onFinish, onBack }: {
  topic: Topic;
  onFinish: () => void;
  onBack: () => void;
}) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [index, setIndex] = useState(0);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [ready, setReady] = useState(false); // 준비 신호 뒤 재생 시작

  const { visible, play } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const finishTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index]);

  // 곧바로 노출되면 당황스러우니, 첫 텍스트 자리에 dot 을 잠깐 깜빡인 뒤 시작한다.
  useEffect(() => {
    const t = window.setTimeout(() => setReady(true), READY_MS);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current;
    const chunks = chunkSentence(script.english, s.unit, s.maxChunkWords);
    setCurrentChunks(chunks);
    play(
      chunks,
      { windowSize: s.windowSize, baseMsPerSyllable: s.baseMsPerSyllable, minDwellMs: MIN_DWELL_MS, hideOld: s.hideOld },
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
  }, [ready, index, topic, play]);

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

      <QuestionBanner topicSeq={topic.topicSeq} />

      <div className="chat">
        {!ready ? (
          <div className="msg">
            <div className="avatar-col">
              <div className="avatar">{speakerInfo(topic.scripts[0].speaker).avatar}</div>
              <div className="avatar-name">{speakerInfo(topic.scripts[0].speaker).name}</div>
            </div>
            <div className="bubble ready-bubble">
              <span className="ready-dots" aria-label="곧 시작"><i /><i /><i /></span>
            </div>
          </div>
        ) : (
          topic.scripts.slice(0, index + 1).map((s, i) => {
            const info = speakerInfo(s.speaker);
            return (
              <DialogBubble
                key={s.seq}
                name={info.name}
                avatar={info.avatar}
                chunks={i === index ? currentChunks : chunkSentence(s.english, settings.unit, settings.maxChunkWords)}
                visible={i === index ? visible : new Set<number>()}
                fadeIn={settings.fadeIn}
                fadeOut={settings.fadeOut}
              />
            );
          })
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
