import { useSettings } from '../settings/SettingsContext';
import './SettingsPanel.css';

export function SettingsPanel() {
  const { settings, setSettings } = useSettings();
  return (
    <div className="settings-panel">
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
        창 크기 N: {settings.windowSize}
        <input
          type="range"
          min={1}
          max={5}
          value={settings.windowSize}
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
        속도(ms/단어): {settings.baseMsPerWord}
        <input
          type="range"
          min={80}
          max={500}
          step={20}
          value={settings.baseMsPerWord}
          onChange={(e) => setSettings({ ...settings, baseMsPerWord: Number(e.target.value) })}
        />
      </label>
    </div>
  );
}
