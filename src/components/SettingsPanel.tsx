import { useState } from 'react';
import { useSettings, type Settings } from '../settings/SettingsContext';
import './SettingsPanel.css';

// 리딩 옵션 프리셋. 처음 쓰는 사람은 여기서 한 번에 고른다.
const PRESETS: { key: string; name: string; desc: string; settings: Settings }[] = [
  { key: 'word', name: '단어', desc: '단어 하나씩', settings: { unit: 'word', windowSize: 4, baseMsPerSyllable: 200, maxChunkWords: 3, hideOld: true, marqueeSpeed: 120 } },
  { key: 'chunk', name: '청크', desc: '여러 단어 묶음', settings: { unit: 'chunk', windowSize: 4, baseMsPerSyllable: 200, maxChunkWords: 3, hideOld: true, marqueeSpeed: 120 } },
  { key: 'accumulate', name: '누적', desc: '청크가 쌓임', settings: { unit: 'chunk', windowSize: 4, baseMsPerSyllable: 200, maxChunkWords: 3, hideOld: false, marqueeSpeed: 120 } },
];

// 지금 설정이 어떤 프리셋인지 판정(무관한 필드는 무시).
function matchesPreset(s: Settings, p: Settings): boolean {
  if (s.unit !== p.unit || s.baseMsPerSyllable !== p.baseMsPerSyllable || s.hideOld !== p.hideOld) return false;
  if (p.unit === 'chunk' && s.maxChunkWords !== p.maxChunkWords) return false;
  if (p.hideOld && s.windowSize !== p.windowSize) return false;
  return true;
}

const OPTION_HELP: { title: string; desc: string }[] = [
  { title: '노출 단위', desc: '한 번에 드러나는 덩어리 — 단어 하나씩 또는 여러 단어 묶음(청크)' },
  { title: '오래된 청크 숨기기', desc: '지나간 덩어리를 지워 되돌아보기 차단 — 끄면 문장 끝까지 쌓임' },
  { title: '창 크기 N', desc: '화면에 동시에 남는 덩어리 개수 — 클수록 여유롭게 보임' },
  { title: '최대 청크 길이', desc: '한 청크에 묶을 최대 단어 수 (청크 모드에서만)' },
  { title: '속도(ms/음절)', desc: '음절 하나당 노출 시간 — 클수록 천천히 넘어감' },
];

export function SettingsPanel() {
  const { settings, setSettings } = useSettings();
  const [showCustom, setShowCustom] = useState(false);

  const activeKey = PRESETS.find((p) => matchesPreset(settings, p.settings))?.key ?? null;

  return (
    <div className="settings-panel">
      <div className="preset-row" role="group" aria-label="옵션 프리셋">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            className={`preset${activeKey === p.key ? ' on' : ''}`}
            aria-pressed={activeKey === p.key}
            onClick={() => setSettings(p.settings)}
          >
            <span className="preset-name">{p.name}</span>
            <span className="preset-desc">{p.desc}</span>
          </button>
        ))}
      </div>

      <button
        type="button"
        className="custom-toggle"
        aria-expanded={showCustom}
        onClick={() => setShowCustom((v) => !v)}
      >
        직접 설정 {showCustom ? '▲' : '▼'}
        {activeKey === null && <span className="custom-badge">커스텀</span>}
      </button>

      {showCustom && (
        <div className="custom-controls">
          <div className="settings-grid">
            <label>
              노출 단위
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
              오래된 청크 숨기기
              <div className="seg-toggle" role="group">
                <button
                  type="button"
                  className={settings.hideOld ? 'on' : ''}
                  onClick={() => setSettings({ ...settings, hideOld: true })}
                >
                  켜기
                </button>
                <button
                  type="button"
                  className={!settings.hideOld ? 'on' : ''}
                  onClick={() => setSettings({ ...settings, hideOld: false })}
                >
                  끄기
                </button>
              </div>
            </label>
            <label style={{ opacity: settings.hideOld ? 1 : 0.4 }}>
              창 크기 N: {settings.windowSize}
              <input
                type="range"
                min={1}
                max={5}
                value={settings.windowSize}
                disabled={!settings.hideOld}
                onChange={(e) => setSettings({ ...settings, windowSize: Number(e.target.value) })}
              />
            </label>
            <label style={{ opacity: settings.unit === 'chunk' ? 1 : 0.4 }}>
              최대 청크 길이: {settings.maxChunkWords}단어
              <input
                type="range"
                min={1}
                max={6}
                value={settings.maxChunkWords}
                disabled={settings.unit !== 'chunk'}
                onChange={(e) => setSettings({ ...settings, maxChunkWords: Number(e.target.value) })}
              />
            </label>
            <label>
              속도(ms/음절): {settings.baseMsPerSyllable}
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

          {/* 옵션 설명은 직접 설정을 펼쳤을 때 맨 아래에 함께 보인다. */}
          <div className="opt-help">
            {OPTION_HELP.map((o) => (
              <div key={o.title}>
                <b>{o.title}</b> — {o.desc}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
