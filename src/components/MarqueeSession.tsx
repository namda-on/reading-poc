import { useEffect, useRef, useState } from 'react';
import type { Script, Topic } from '../data/types';
import { useSettings } from '../settings/SettingsContext';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';
import './DialogBubble.css';
import './MarqueeSession.css';

// 다음 말풍선을 이어 등장시킬 때의 여백(px). 문장 사이 간격 → 연속 흐름 유지.
const NEXT_GAP_PX = 90;
const MIN_DURATION_MS = 800;
const INTRO_MS = 1000; // 대화 시작 전 문제만 먼저 노출하는 시간

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

// 말풍선 하나: 자기 텍스트를 오른쪽→왼쪽으로 한 번 흘려보낸다(자체 애니메이션).
function MarqueeBubble({ script, speed, onReadyForNext, onFinished }: {
  script: Script;
  speed: number;
  onReadyForNext?: () => void; // 다음 말풍선을 이어 등장시킬 시점
  onFinished?: () => void; // 완전히 빠져나간 시점(마지막 말풍선 → 퀴즈)
}) {
  const info = speakerInfo(script.speaker);
  const laneRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const lane = laneRef.current;
    const text = textRef.current;
    if (!lane || !text) return;

    const laneW = lane.clientWidth;
    const textW = text.scrollWidth;
    const px = Math.max(20, speed); // px/s
    const durationMs = Math.max(MIN_DURATION_MS, ((laneW + textW) / px) * 1000);

    const anim = text.animate(
      [{ transform: `translateX(${laneW}px)` }, { transform: `translateX(${-textW}px)` }],
      { duration: durationMs, easing: 'linear', fill: 'forwards' },
    );
    if (onFinished) anim.onfinish = onFinished;

    // 문장 전체가 레인에 들어온 뒤(=자기 폭 + 여백만큼 이동) 다음을 이어 등장.
    let nextTimer: number | null = null;
    if (onReadyForNext) {
      const nextAtMs = Math.min(durationMs, ((textW + NEXT_GAP_PX) / px) * 1000);
      nextTimer = window.setTimeout(onReadyForNext, nextAtMs);
    }

    return () => {
      anim.cancel();
      if (nextTimer) window.clearTimeout(nextTimer);
    };
    // 마운트 시 1회만 구동한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="msg">
      <div className="avatar-col">
        <div className="avatar">{info.avatar}</div>
        <div className="avatar-name">{info.name}</div>
      </div>
      <div className="bubble marquee-bubble" ref={laneRef}>
        <span className="marquee-text" ref={textRef}>{script.english}</span>
      </div>
    </div>
  );
}

export function MarqueeSession({ topic, onFinish, onBack }: {
  topic: Topic;
  onFinish: () => void;
  onBack: () => void;
}) {
  const { settings } = useSettings();
  const speed = settings.marqueeSpeed;
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const total = topic.scripts.length;
  const [intro, setIntro] = useState(true); // 문제를 먼저 보여주는 인트로 단계
  const [revealed, setRevealed] = useState(1); // 등장한 말풍선 수
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [revealed]);

  // 문제를 먼저 노출한 뒤 전광판 흐름을 시작한다.
  useEffect(() => {
    const t = window.setTimeout(() => setIntro(false), INTRO_MS);
    return () => window.clearTimeout(t);
  }, []);

  const progressPct = Math.round((revealed / total) * 100);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🪧</div>
          <div className="bar">
            <span className="bar-count">{revealed}/{total}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>
      </header>

      <QuestionBanner topicSeq={topic.topicSeq} />

      <div className="chat">
        {topic.scripts.slice(0, intro ? 0 : revealed).map((s, i) => (
          <MarqueeBubble
            key={s.seq}
            script={s}
            speed={speed}
            onReadyForNext={i < total - 1 ? () => setRevealed((r) => Math.max(r, i + 2)) : undefined}
            onFinished={i === total - 1 ? () => onFinishRef.current() : undefined}
          />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
