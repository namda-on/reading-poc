import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

export interface Settings {
  unit: 'word' | 'chunk';
  windowSize: number;
  baseMsPerSyllable: number;
  maxChunkWords: number;
  hideOld: boolean; // 오래된 청크 숨기기(창 크기 적용). false 면 문장 끝까지 누적.
  fadeIn: boolean; // 청크 등장 페이드. false 면 즉시 나타남.
  fadeOut: boolean; // 청크 사라짐 페이드. false 면 즉시 사라짐.
  marqueeSpeed: number; // 전광판 흐름 속도(px/초).
}

export const DEFAULT_SETTINGS: Settings = { unit: 'word', windowSize: 4, baseMsPerSyllable: 200, maxChunkWords: 3, hideOld: true, fadeIn: false, fadeOut: true, marqueeSpeed: 120 };

const STORAGE_KEY = 'reading-poc:settings';

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    // 저장된 값이 일부만 있어도 기본값으로 채운다.
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<Settings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

const Ctx = createContext<{ settings: Settings; setSettings: (s: Settings) => void } | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadSettings);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // localStorage 사용 불가 환경은 무시(휘발성으로 동작).
    }
  }, [settings]);

  return <Ctx.Provider value={{ settings, setSettings }}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useSettings must be used within SettingsProvider');
  return v;
}
