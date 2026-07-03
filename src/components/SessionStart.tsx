import { useState } from 'react';
import type { Mode, Topic } from '../data/types';
import { SettingsPanel } from './SettingsPanel';
import './ReadingSession.css';
import './SessionStart.css';

const MODES: { value: Mode; label: string; icon: string; desc: string }[] = [
  { value: 'reading', label: '리딩', icon: '📖', desc: '청크가 창을 따라 슬라이딩하며 노출' },
  { value: 'listening', label: '리스닝', icon: '🎧', desc: '텍스트 없이 실제 음성만 듣기' },
];

export function SessionStart({ topic, onStart, onBack }: {
  topic: Topic;
  onStart: (mode: Mode) => void;
  onBack: () => void;
}) {
  const [mode, setMode] = useState<Mode>('reading');

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

        <button className="start-btn" onClick={() => onStart(mode)}>▶ 시작</button>
      </div>
    </div>
  );
}
