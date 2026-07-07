import { useState } from 'react';
import type { Mode, Topic } from '../data/types';
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

export function SessionStart({ topic, onStart, onBack, initialMode = 'reading' }: {
  topic: Topic;
  onStart: (mode: Mode) => void;
  onBack: () => void;
  initialMode?: Mode; // 마지막에 고른 모드를 기본 선택으로
}) {
  const { settings, setSettings } = useSettings();
  const [mode, setMode] = useState<Mode>(initialMode);

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

        {/* 전광판은 흐름 속도만 조절한다. */}
        {mode === 'marquee' && (
          <div className="start-settings">
            <div className="settings-panel">
              <label>
                흐름 속도(px/초): {settings.marqueeSpeed}
                <span className="opt-desc">문구가 흐르는 빠르기 — 클수록 빨리 지나감</span>
                <input
                  type="range"
                  min={40}
                  max={240}
                  step={20}
                  value={settings.marqueeSpeed}
                  onChange={(e) => setSettings({ ...settings, marqueeSpeed: Number(e.target.value) })}
                />
              </label>
            </div>
          </div>
        )}

        <button className="start-btn" onClick={() => onStart(mode)}>▶ 시작</button>
      </div>
    </div>
  );
}
