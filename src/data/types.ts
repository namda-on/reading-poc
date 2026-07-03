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
