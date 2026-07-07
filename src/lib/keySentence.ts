import type { Script } from '../data/types';

export interface KeySentence {
  english: string;
  translated: string;
  audioUrl: string | null;
}

// 문장 단위로 분리(. ! ? 기준). 부호 보존.
function splitSentences(text: string): string[] {
  const m = (text || '').match(/[^.!?]+[.!?]*/g);
  return (m ?? [text]).map((s) => s.trim()).filter(Boolean);
}

// 한국어 겹침 비교용 글자 바이그램(한글·숫자만).
function bigrams(text: string): string[] {
  const clean = (text || '').replace(/[^가-힣0-9]/g, '');
  const out: string[] = [];
  for (let i = 0; i < clean.length - 1; i++) out.push(clean.slice(i, i + 2));
  return out;
}
function overlap(a: string, b: string): number {
  const set = new Set(bigrams(b));
  let n = 0;
  for (const g of bigrams(a)) if (set.has(g)) n++;
  return n;
}

const wordCount = (s: string) => s.trim().split(/\s+/).length;

// 배열·받아쓰기 문제에 쓸 '핵심 1문장'을 고른다.
// - 항상 단일 문장(여러 문장이 든 스크립트는 문장 단위로 쪼갬).
// - 퀴즈(질문·해설·정답)와 한국어가 가장 많이 겹치는 문장 = 정답을 맞히는 데 필요한 문장.
// - 퀴즈 힌트가 없거나 겹침이 없으면 3~9단어의 가장 긴 문장으로 폴백.
export function pickKeySentence(scripts: Script[], quizHint = ''): KeySentence {
  type Cand = { english: string; translated: string; audioUrl: string | null; wc: number; score: number };
  const cands: Cand[] = [];
  for (const s of scripts) {
    const en = splitSentences(s.english);
    const ko = splitSentences(s.translated || '');
    en.forEach((e, i) => {
      const wc = wordCount(e);
      if (wc < 2) return; // 너무 짧은 조각 제외
      cands.push({
        english: e,
        translated: (ko[i] || s.translated || '').trim(),
        audioUrl: s.audioUrl ?? null,
        wc,
        score: quizHint ? overlap(ko[i] || s.translated || '', quizHint) : 0,
      });
    });
  }
  if (!cands.length) {
    const s = scripts[0];
    return { english: s.english, translated: s.translated, audioUrl: s.audioUrl ?? null };
  }
  const inRange = (c: Cand) => (c.wc >= 3 && c.wc <= 9 ? 1 : 0);
  cands.sort((a, b) => b.score - a.score || inRange(b) - inRange(a) || b.wc - a.wc);
  const best = cands[0];
  return { english: best.english, translated: best.translated, audioUrl: best.audioUrl };
}
