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
  'and', 'but', 'or', 'so', 'because', 'that', 'which', 'who', 'whom', 'whose',
  'when', 'while', 'if', 'how', 'what', 'where', 'why',
  'do', 'does', 'did',
  'really', 'very', 'just', 'quite',
  'today', 'tomorrow', 'yesterday', 'tonight', 'now', 'soon', 'later',
  'to', 'in', 'on', 'at', 'for', 'with', 'from', 'of', 'about', 'into', 'over', 'after', 'before', 'as', 'than',
]);

// 주어 대명사. 이 단어 '뒤'에서 끊어 주어부/술어부를 나눈다(you 는 do you need? 처럼 붙어야 해 제외).
const SUBJECT_PRONOUNS = new Set(['i', 'he', 'she', 'we', 'they', 'it']);

// 한 덩어리로 유지할 고정표현(소문자, 공백 구분).
// 명사구는 '앞에서 끊어' 새 덩어리로, 동사구는 앞을 끊지 않고 앞말(주어 등)에 붙인다.
const NOUN_PHRASES = ['a lot of', 'in front of', 'the same as', 'as well as', 'a couple of'];
const VERB_PHRASES = ['want to', 'have to', 'need to', 'going to', 'used to', 'able to'];
const FIXED_PHRASES = [...NOUN_PHRASES, ...VERB_PHRASES].sort((a, b) => b.length - a.length);

const norm = (w: string) => w.replace(/[^a-zA-Z']/g, '').toLowerCase();
const isUpperStart = (t: string) => /^[A-Z]/.test(t);
const isIWord = (t: string) => /^I('|$)/.test(t); // I, I'm, I'll — 대문자지만 고유명사 아님
const endsSentence = (t: string) => /[.!?]['")\]]*$/.test(t);
const endsClause = (t: string) => /[,;:]['")\]]*$/.test(t);

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

export function chunkByRule(sentence: string, maxWords = Infinity): Chunk[] {
  const tokens = tokenize(sentence);
  const words = tokens.map((t) => norm(t.text));

  // 고정표현: 명사구는 시작을 경계로(phraseStart), 모든 고정표현의 중간 토큰은 경계 금지(lockedStart).
  const lockedStart = new Set<number>();
  const phraseStart = new Set<number>();
  for (let i = 0; i < tokens.length; i++) {
    for (const phrase of FIXED_PHRASES) {
      const parts = phrase.split(' ');
      if (words.slice(i, i + parts.length).join(' ') === phrase) {
        if (NOUN_PHRASES.includes(phrase)) phraseStart.add(i);
        for (let k = i + 1; k < i + parts.length; k++) lockedStart.add(k);
        break;
      }
    }
  }

  // 1) 의미 경계로 토큰 그룹핑
  const groups: Token[][] = [];
  let cur: Token[] = [];
  const flush = () => {
    if (cur.length) groups.push(cur);
    cur = [];
  };
  for (let i = 0; i < tokens.length; i++) {
    if (i > 0) {
      const prev = tokens[i - 1].text;
      const afterSentenceEnd = endsSentence(prev); // 문장 끝 뒤는 무조건 끊음
      const afterClause = endsClause(prev); // 쉼표/세미콜론/콜론 뒤
      // 주어 대명사 뒤: 주어부/술어부 분리. 대명사가 홀로 남지 않게 현재 덩어리 2토큰 이상일 때만.
      const afterPronoun = SUBJECT_PRONOUNS.has(words[i - 1]) && cur.length >= 2;
      // 고유명사(대문자로 시작) 앞: 단, 전치사/접속사 뒤(그 목적어)거나 고유명사가 이어질 땐 붙인다.
      const properNoun =
        isUpperStart(tokens[i].text) && !isIWord(tokens[i].text) &&
        !afterSentenceEnd && !afterClause && !isUpperStart(prev) && !BREAK_BEFORE.has(words[i - 1]);
      const breakBeforeWord = BREAK_BEFORE.has(words[i]) || phraseStart.has(i);
      const startsNewChunk =
        afterSentenceEnd ||
        (!lockedStart.has(i) && (afterClause || afterPronoun || properNoun || breakBeforeWord));
      if (startsNewChunk) flush();
    }
    cur.push(tokens[i]);
  }
  flush();

  // 2) 최대 길이 초과 그룹은 단어 경계에서 강제 분할
  const chunks: Chunk[] = [];
  const step = maxWords >= 1 ? maxWords : Infinity;
  for (const g of groups) {
    for (let i = 0; i < g.length; i += step) {
      const slice = g.slice(i, i + step);
      chunks.push({
        text: slice.map((t) => t.text).join(' '),
        start: slice[0].start,
        end: slice[slice.length - 1].end,
      });
    }
  }
  return chunks;
}

export function chunkSentence(
  sentence: string,
  unit: 'word' | 'chunk',
  maxChunkWords = Infinity,
): Chunk[] {
  return unit === 'word' ? chunkByWord(sentence) : chunkByRule(sentence, maxChunkWords);
}
