export interface Chunk {
  text: string;
  start: number;
  end: number;
}

export interface Token {
  text: string;
  start: number;
  end: number;
}

// 청크 경계를 '앞에서 끊는' 트리거 단어. 부호를 뗀 소문자로 비교.
const BREAK_BEFORE = new Set([
  'and', 'but', 'or', 'so', 'because', 'that', 'which', 'who', 'when', 'while', 'if',
  'to', 'in', 'on', 'at', 'for', 'with', 'from', 'of', 'about', 'into', 'over', 'after', 'before',
]);

// 한 덩어리로 유지할 고정표현(소문자, 공백 구분). 긴 것 우선 매칭.
const FIXED_PHRASES = [
  'a lot of', 'in front of', 'the same as', 'as well as', 'a couple of',
  'want to', 'have to', 'need to', 'going to', 'used to', 'able to',
].sort((a, b) => b.length - a.length);

const norm = (w: string) => w.replace(/[^a-zA-Z']/g, '').toLowerCase();

export function tokenize(sentence: string): Token[] {
  const out: Token[] = [];
  const re = /\S+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(sentence))) out.push({ text: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

export function chunkByWord(sentence: string): Chunk[] {
  return tokenize(sentence).map((t) => ({ text: t.text, start: t.start, end: t.end }));
}

export function chunkByRule(sentence: string): Chunk[] {
  const tokens = tokenize(sentence);
  const words = tokens.map((t) => norm(t.text));

  // 고정표현: 시작 인덱스는 경계로 삼고(phraseStart), 중간 토큰은 경계 금지(lockedStart)
  const lockedStart = new Set<number>();
  const phraseStart = new Set<number>();
  for (let i = 0; i < tokens.length; i++) {
    for (const phrase of FIXED_PHRASES) {
      const parts = phrase.split(' ');
      if (words.slice(i, i + parts.length).join(' ') === phrase) {
        phraseStart.add(i);
        for (let k = i + 1; k < i + parts.length; k++) lockedStart.add(k);
        break;
      }
    }
  }

  const chunks: Chunk[] = [];
  let cur: Token[] = [];
  const flush = () => {
    if (!cur.length) return;
    chunks.push({
      text: cur.map((t) => t.text).join(' '),
      start: cur[0].start,
      end: cur[cur.length - 1].end,
    });
    cur = [];
  };
  for (let i = 0; i < tokens.length; i++) {
    const startsNewChunk =
      i > 0 && !lockedStart.has(i) && (BREAK_BEFORE.has(words[i]) || phraseStart.has(i));
    if (startsNewChunk) flush();
    cur.push(tokens[i]);
  }
  flush();
  return chunks;
}

export function chunkSentence(sentence: string, unit: 'word' | 'chunk'): Chunk[] {
  return unit === 'word' ? chunkByWord(sentence) : chunkByRule(sentence);
}
