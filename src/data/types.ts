export interface Token {
  text: string;
  start: number;
  end: number;
}

export interface Script {
  seq: number;
  speaker: 'A' | 'B';
  english: string;
  translated: string;
  hint?: string;
  // 리스닝 모드 TTS 오디오(speech.epop.ai). 없으면 null.
  audioUrl: string | null;
  // tagList 원본 보존용(provenance). 앱 청킹에는 쓰지 않는다.
  words?: Token[];
}

export interface Topic {
  topicSeq: number;
  title: string;
  partner: string;
  scripts: Script[];
}

export interface Story {
  courseSeq: number;
  title: string;
  subtitle: string;
  topics: Topic[];
}

export interface DialogsData {
  level: number;
  stories: Story[];
}

// 세션 재생 방식: 리딩(슬라이딩) / 리스닝(TTS) / 전광판(가로 흐름) / 고정(제자리 RSVP).
export type Mode = 'reading' | 'listening' | 'marquee' | 'fixed';
