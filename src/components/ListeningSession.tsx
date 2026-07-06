import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';
import './DialogBubble.css';
import './ListeningSession.css';

const GAP_MS = 500; // 문장 사이 간격
const FINISH_GAP_MS = 700; // 마지막 오디오 후 퀴즈로 넘어가기 전 여유
const INTRO_MS = 1000; // 대화 시작 전 문제만 먼저 노출하는 시간

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

export function ListeningSession({ topic, onFinish, onBack }: {
  topic: Topic;
  onFinish: () => void;
  onBack: () => void;
}) {
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [index, setIndex] = useState(0);
  const [intro, setIntro] = useState(true); // 문제를 먼저 보여주는 인트로 단계
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [index]);

  // 문제를 먼저 노출한 뒤 오디오를 시작한다.
  useEffect(() => {
    const t = window.setTimeout(() => setIntro(false), INTRO_MS);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (intro) return;
    const script = topic.scripts[index];
    if (!script) return;
    const audio = audioRef.current;
    if (!audio) return;

    let cancelled = false;
    let gap: number | null = null;

    const advance = () => {
      if (cancelled) return;
      if (index + 1 >= topic.scripts.length) {
        gap = window.setTimeout(() => onFinishRef.current(), FINISH_GAP_MS);
      } else {
        gap = window.setTimeout(() => setIndex((i) => i + 1), GAP_MS);
      }
    };

    audio.addEventListener('ended', advance);
    audio.addEventListener('error', advance); // 오디오 누락 시 멈추지 않고 다음으로

    if (script.audioUrl) {
      audio.src = script.audioUrl;
      audio.currentTime = 0;
      // 시작 버튼 클릭이라는 사용자 제스처 직후이므로 자동재생이 허용된다.
      audio.play().catch(advance);
    } else {
      advance();
    }

    return () => {
      cancelled = true;
      audio.removeEventListener('ended', advance);
      audio.removeEventListener('error', advance);
      audio.pause();
      if (gap) window.clearTimeout(gap);
    };
  }, [intro, index, topic]);

  const total = topic.scripts.length;
  const progressPct = Math.round(((index + 1) / total) * 100);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🎧</div>
          <div className="bar">
            <span className="bar-count">{index + 1}/{total}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>
      </header>

      <audio ref={audioRef} preload="auto" />

      <QuestionBanner topicSeq={topic.topicSeq} />

      <div className="chat">
        {topic.scripts.slice(0, intro ? 0 : index + 1).map((s, i) => {
          const info = speakerInfo(s.speaker);
          const playing = i === index;
          return (
            <div className="msg" key={s.seq}>
              <div className="avatar-col">
                <div className="avatar">{info.avatar}</div>
                <div className="avatar-name">{info.name}</div>
              </div>
              <div className={`bubble hidden-bubble${playing ? ' playing' : ''}`}>
                <span className="wave"><i /><i /><i /></span>
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
