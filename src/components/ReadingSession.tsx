import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence, type Chunk } from '../lib/chunk';
import { useSlidingReveal } from '../hooks/useSlidingReveal';
import { useSettings } from '../settings/SettingsContext';
import { DialogBubble } from './DialogBubble';
import { SettingsPanel } from './SettingsPanel';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';

const MIN_DWELL_MS = 100; // 하한. 너무 높으면 짧은 단어가 바닥에 걸려 속도 설정이 무력화된다.
const GAP_MS = 400;
const FADE_OUT_MS = 500; // 마지막 청크가 페이드아웃(CSS 450ms)된 뒤 문제로 넘어감
const INTRO_MS = 1000; // 대화 시작 전 문제 + 준비 dot 을 함께 잠깐 노출

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
  const [intro, setIntro] = useState(true); // 문제 + 준비 dot 을 보여주는 인트로 단계

  const { visible, play } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);
  const finishTimer = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index]);

  // 문제 + 준비 dot 을 잠깐 보여준 뒤 대화를 시작한다.
  useEffect(() => {
    const t = window.setTimeout(() => setIntro(false), INTRO_MS);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (intro) return;
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
  }, [intro, index, topic, play]);

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
        {intro ? (
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
