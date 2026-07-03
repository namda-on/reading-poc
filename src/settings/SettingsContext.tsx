import { createContext, useContext, useState, type ReactNode } from 'react';

export interface Settings {
  unit: 'word' | 'chunk';
  windowSize: number;
  baseMsPerWord: number;
}

export const DEFAULT_SETTINGS: Settings = { unit: 'chunk', windowSize: 2, baseMsPerWord: 220 };

const Ctx = createContext<{ settings: Settings; setSettings: (s: Settings) => void } | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  return <Ctx.Provider value={{ settings, setSettings }}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useSettings must be used within SettingsProvider');
  return v;
}
