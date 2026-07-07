import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { useSettings } from '../settings/SettingsContext';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';
import './MarqueeStreamSession.css';

const INTRO_MS = 1000;
const GAP_MS = 250; // 문장 사이 짧은 간격
const MIN_DURATION_MS = 800;

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

// 전광판 '한 줄' 방식: 고정된 한 줄 레인에서 문장 전체가 오른쪽→왼쪽으로 연속으로 흘러 지나간다.
export function MarqueeStreamSession({ topic, onFinish, onBack, showQuestion = true }: {
  topic: Topic;
  onFinish: () => void;
  onBack: () => void;
  showQuestion?: boolean;
}) {
  const { settings } = useSettings();
  const speedRef = useRef(settings.marqueeSpeed);
  speedRef.current = settings.marqueeSpeed;
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [index, setIndex] = useState(0);
  const [intro, setIntro] = useState(true);
  const laneRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setIntro(false), INTRO_MS);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (intro) return;
    const lane = laneRef.current;
    const span = textRef.current;
    if (!lane || !span) return;

    let cancelled = false;
    let gap: number | null = null;
    const laneW = lane.clientWidth;
    const textW = span.scrollWidth;
    const speed = Math.max(20, speedRef.current); // px/s
    const durationMs = Math.max(MIN_DURATION_MS, ((laneW + textW) / speed) * 1000);

    const anim = span.animate(
      [{ transform: `translateX(${laneW}px)` }, { transform: `translateX(${-textW}px)` }],
      { duration: durationMs, easing: 'linear', fill: 'forwards' },
    );
    anim.onfinish = () => {
      if (cancelled) return;
      if (index + 1 < topic.scripts.length) gap = window.setTimeout(() => setIndex((i) => i + 1), GAP_MS);
      else onFinishRef.current();
    };
    return () => {
      cancelled = true;
      anim.cancel();
      if (gap) window.clearTimeout(gap);
    };
  }, [intro, index, topic]);

  const total = topic.scripts.length;
  const progressPct = Math.round(((index + 1) / total) * 100);
  const info = speakerInfo(topic.scripts[index].speaker);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🪧</div>
          <div className="bar">
            <span className="bar-count">{index + 1}/{total}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>
      </header>

      {showQuestion && <QuestionBanner topicSeq={topic.topicSeq} />}

      <div className="ms-stage">
        <div className="ms-speaker">
          <span className="ms-avatar">{info.avatar}</span>
          {info.name}
        </div>
        <div className="ms-lane" ref={laneRef}>
          <span className="ms-text" key={index} ref={textRef}>{intro ? '' : topic.scripts[index].english}</span>
        </div>
      </div>
    </div>
  );
}
