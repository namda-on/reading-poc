import { useState } from 'react';
import type { Mode, QuizType, Topic } from '../data/types';
import { useSettings } from '../settings/SettingsContext';
import { SettingsPanel } from './SettingsPanel';
import './ReadingSession.css';
import './SessionStart.css';

const MODES: { value: Mode; label: string; icon: string; desc: string }[] = [
  { value: 'reading', label: '리딩', icon: '📖', desc: '청크가 창을 따라 슬라이딩' },
  { value: 'listening', label: '리스닝', icon: '🎧', desc: '텍스트 없이 실제 음성' },
  { value: 'marquee', label: '전광판', icon: '🪧', desc: '문구가 오른쪽→왼쪽 흐름' },
  { value: 'fixed', label: '고정', icon: '🎯', desc: '한 자리에서 제자리 교체' },
];

const QUIZ_TYPES: { value: QuizType; label: string }[] = [
  { value: 'comprehension', label: '이해' },
  { value: 'arrange', label: '단어 배열' },
  { value: 'dictation', label: '받아쓰기' },
];

export function SessionStart({ topic, onStart, onBack, initialMode = 'reading', initialQuizType = 'comprehension' }: {
  topic: Topic;
  onStart: (mode: Mode, quizType: QuizType) => void;
  onBack: () => void;
  initialMode?: Mode; // 마지막에 고른 모드를 기본 선택으로
  initialQuizType?: QuizType; // 마지막에 고른 문제 유형을 기본 선택으로
}) {
  const { settings, setSettings } = useSettings();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [quizType, setQuizType] = useState<QuizType>(initialQuizType);

  return (
    <div className="session">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <div className="start-title">Episode {topic.topicSeq}</div>
      </header>

      <div className="start-prompt">
        <p>모드를 고르고 시작하세요.</p>

        <div className="mode-cards" role="group" aria-label="모드 선택">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              className={`mode-card${mode === m.value ? ' on' : ''}`}
              onClick={() => setMode(m.value)}
              aria-pressed={mode === m.value}
            >
              <span className="mode-icon">{m.icon}</span>
              <span className="mode-label">{m.label}</span>
              <span className="mode-desc">{m.desc}</span>
            </button>
          ))}
        </div>

        {/* 리딩 노출 설정은 리딩 모드에서만 의미가 있다. */}
        {mode === 'reading' && (
          <div className="start-settings">
            <SettingsPanel />
          </div>
        )}

        {/* 고정 모드는 노출 단위와 속도만 따른다(창·페이드 등은 무관). */}
        {mode === 'fixed' && (
          <div className="start-settings">
            <div className="settings-panel">
              <label>
                노출 단위
                <span className="opt-desc">한 자리에서 단어 하나씩 또는 청크 단위로 교체</span>
                <div className="seg-toggle" role="group">
                  <button
                    type="button"
                    className={settings.unit === 'word' ? 'on' : ''}
                    onClick={() => setSettings({ ...settings, unit: 'word' })}
                  >
                    단어
                  </button>
                  <button
                    type="button"
                    className={settings.unit === 'chunk' ? 'on' : ''}
                    onClick={() => setSettings({ ...settings, unit: 'chunk' })}
                  >
                    청크
                  </button>
                </div>
              </label>
              <label>
                속도(ms/음절): {settings.baseMsPerSyllable}
                <span className="opt-desc">한 단위가 머무는 시간 — 클수록 천천히 교체</span>
                <input
                  type="range"
                  min={60}
                  max={400}
                  step={20}
                  value={settings.baseMsPerSyllable}
                  onChange={(e) => setSettings({ ...settings, baseMsPerSyllable: Number(e.target.value) })}
                />
              </label>
            </div>
          </div>
        )}

        {/* 전광판: 흐름 방식(문장/낱개) + 속도. 낱개면 노출 단위도 조절. */}
        {mode === 'marquee' && (
          <div className="start-settings">
            <div className="settings-panel">
              <label>
                흐름 방식
                <span className="opt-desc">문장별 말풍선 vs 한 줄에서 문장 전체가 연속으로 흐름</span>
                <div className="seg-toggle" role="group">
                  <button
                    type="button"
                    className={settings.marqueeStyle === 'sentence' ? 'on' : ''}
                    onClick={() => setSettings({ ...settings, marqueeStyle: 'sentence' })}
                  >
                    문장별
                  </button>
                  <button
                    type="button"
                    className={settings.marqueeStyle === 'stream' ? 'on' : ''}
                    onClick={() => setSettings({ ...settings, marqueeStyle: 'stream' })}
                  >
                    한 줄
                  </button>
                </div>
              </label>
              <label>
                흐름 속도(px/초): {settings.marqueeSpeed}
                <span className="opt-desc">문구가 흐르는 빠르기 — 클수록 빨리 지나감</span>
                <input
                  type="range"
                  min={40}
                  max={400}
                  step={20}
                  value={settings.marqueeSpeed}
                  onChange={(e) => setSettings({ ...settings, marqueeSpeed: Number(e.target.value) })}
                />
              </label>
            </div>
          </div>
        )}

        {/* 세션 후 풀 문제 유형(다시 풀 때 지루하지 않게 바꿀 수 있다). */}
        <div className="quiztype-row">
          <span className="quiztype-label">문제 유형</span>
          <div className="seg-toggle" role="group" aria-label="문제 유형">
            {QUIZ_TYPES.map((q) => (
              <button
                key={q.value}
                type="button"
                className={quizType === q.value ? 'on' : ''}
                onClick={() => setQuizType(q.value)}
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>

        <button className="start-btn" onClick={() => onStart(mode, quizType)}>▶ 시작</button>
      </div>
    </div>
  );
}
