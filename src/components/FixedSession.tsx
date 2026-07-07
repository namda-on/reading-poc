import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence } from '../lib/chunk';
import { dwellMs } from '../lib/reveal';
import { useSettings } from '../settings/SettingsContext';
import { QuestionBanner } from './QuestionBanner';
import './ReadingSession.css';
import './FixedSession.css';

const MIN_DWELL_MS = 100;
const GAP_MS = 350; // 문장 사이 간격
const INTRO_MS = 1000; // 대화 시작 전 문제만 먼저 노출

function speakerInfo(speaker: 'A' | 'B') {
  return speaker === 'A' ? { name: 'A', avatar: '🐻' } : { name: 'B', avatar: '🐰' };
}

// 시선 고정(RSVP) 모드: 한 자리에서 단어/청크가 제자리 교체된다. 화자·진행으로 대화 맥락 유지.
export function FixedSession({ topic, onFinish, onBack }: {
  topic: Topic;
  onFinish: () => void;
  onBack: () => void;
}) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  const [index, setIndex] = useState(0); // 현재 스크립트
  const [chunkIdx, setChunkIdx] = useState(-1); // 현재 스크립트 내 청크
  const [chunks, setChunks] = useState<string[]>([]);
  const [intro, setIntro] = useState(true);

  useEffect(() => {
    const t = window.setTimeout(() => setIntro(false), INTRO_MS);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (intro) return;
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current;
    const cs = chunkSentence(script.english, s.unit, s.maxChunkWords).map((c) => c.text);
    setChunks(cs);
    setChunkIdx(cs.length ? 0 : -1);

    let cancelled = false;
    const timers: number[] = [];
    const rs = { windowSize: 1, baseMsPerSyllable: s.baseMsPerSyllable, minDwellMs: MIN_DWELL_MS };
    let acc = 0;
    cs.forEach((text, i) => {
      if (i > 0) {
        const at = acc;
        timers.push(window.setTimeout(() => { if (!cancelled) setChunkIdx(i); }, at));
      }
      acc += dwellMs({ text, start: 0, end: text.length }, rs);
    });
    timers.push(window.setTimeout(() => {
      if (cancelled) return;
      if (index + 1 >= topic.scripts.length) onFinishRef.current();
      else setIndex((i) => i + 1);
    }, acc + GAP_MS));

    return () => {
      cancelled = true;
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [intro, index, topic]);

  const total = topic.scripts.length;
  const progressPct = Math.round(((index + 1) / total) * 100);
  const info = speakerInfo(topic.scripts[index].speaker);
  const word = intro ? '' : (chunkIdx >= 0 ? chunks[chunkIdx] : '');

  return (
    <div className="session fixed-session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="progress">
          <div className="trophy">🎯</div>
          <div className="bar">
            <span className="bar-count">{index + 1}/{total}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        </div>
      </header>

      <QuestionBanner topicSeq={topic.topicSeq} />

      <div className="fixed-stage">
        {/* 대화 맥락: 지금 누구 말인지 */}
        <div className="fixed-speaker">
          <span className="fixed-avatar">{info.avatar}</span>
          {info.name}
        </div>
        {/* 시선 고정 지점: 한 자리에서 교체 */}
        <div className="fixed-focus">
          {intro ? (
            <span className="fixed-dots" aria-label="곧 시작"><i /><i /><i /></span>
          ) : (
            <span className="fixed-word" key={`${index}-${chunkIdx}`}>{word}</span>
          )}
        </div>
      </div>
    </div>
  );
}
