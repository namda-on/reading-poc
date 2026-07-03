# 리딩 모드 POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 리스닝 불가 환경을 위한 리딩 모드를 만든다 — 문장 크기 말풍선 위를 N개 창이 슬라이딩하며 청크를 노출하고, 끝나면 한국어 객관식 문제를 푼다.

**Architecture:** Vite + React + TS SPA. 대화 데이터는 `conversation-agent/server.sqlite`에서 일회성 추출해 정적 JSON으로 커밋(서버 의존 0). 순수 로직(청킹·노출 스케줄)은 타이머 없이 테스트 가능한 함수로 분리하고, 훅·컴포넌트가 이를 구동한다.

**Tech Stack:** Vite, React 18, TypeScript, Vitest, python3(stdlib sqlite3, 추출 스크립트).

## Global Constraints

- 대화 데이터 출처: `/Users/namda/sayvoca/conversation-agent/server.sqlite`, 테이블 `ConversationDialogScriptKR`(스크립트), `ResourceFileKR` name=`ConversationCourses`(코스/토픽).
- 콘텐츠 고정: courseSeq **25**(스티브 잡스), level **2**(A2). 22개 토픽.
- seq 매핑: `dialogSeq = floor(scriptSeq/100)`, `topicSeq = floor(dialogSeq/10)`, `level = dialogSeq % 10`. 즉 topic·level 스크립트 seq 범위 = `(topicSeq*10+level)*100 .. +99`.
- 토큰화: **문장 문자열을 직접 파싱**한다(공백 구분, 문장부호는 앞 토큰에 붙임). tagList는 `!`/`?` 등을 제외하므로 표시용 청크에는 쓰지 않는다(문장부호 유실 방지). tagList는 fixture에 보존만.
- 주석·문서 한국어. 실험 축 3개: 노출 단위(word/chunk)·창 크기 N·기본 속도(ms/단어).
- **설정 변경 semantics(확정):** 노출 단위·N·속도 변경은 **현재 재생 중인 문장에는 영향 없음**. 다음 문장(자동 진행) 또는 "다시 보기"부터 반영한다. → hook은 재생 시작 시점의 chunks·settings를 인자로 받아 고정.
- 안 함: 서버 로깅, 방식2(전광판), 런타임 sqlite/LLM, A2 외 레벨, 로그인, pause(재생/리플레이만).

---

### Task 1: 프로젝트 스캐폴딩 (Vite React-TS + Vitest)

**Files:**
- Create: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`(임시), `vitest.config.ts`
- Create: `.gitignore`

**Interfaces:**
- Consumes: 없음
- Produces: 빌드·테스트 가능한 빈 React 앱. `npm run dev`, `npm test`.

- [ ] **Step 1: Vite react-ts 템플릿 생성 (현재 디렉토리에)**

```bash
cd /Users/namda/sayvoca/reading-poc
npm create vite@latest . -- --template react-ts
npm install
npm install -D vitest
```

디렉토리가 비어있지 않다는 경고가 나오면(docs/ 존재) "Ignore files and continue" 선택.

- [ ] **Step 2: vitest 설정 추가**

Create `vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
});
```

`package.json`의 `scripts`에 추가:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 3: 빌드·테스트 스모크 확인**

Run: `npm run build`
Expected: 성공(dist 생성)

Run: `npm test`
Expected: "No test files found" (에러 아님, exit 0 또는 no-tests 메시지)

- [ ] **Step 4: .gitignore 확인 후 커밋**

`node_modules`, `dist`가 무시되는지 확인.

```bash
git add -A
git commit -m "chore: Vite React-TS + Vitest 스캐폴딩"
```

---

### Task 2: 대화 데이터 추출 스크립트 → dialogs.json

**Files:**
- Create: `scripts/extract.py`
- Create (산출물, 커밋): `src/data/dialogs.json`
- Create: `src/data/types.ts`

**Interfaces:**
- Produces:
  - `src/data/types.ts`:
    ```ts
    export interface Token { text: string; start: number; end: number }
    export interface Script { seq: number; speaker: 'A' | 'B'; english: string; translated: string; hint?: string; words?: Token[] }
    export interface Topic { topicSeq: number; title: string; partner: string; scripts: Script[] }
    export interface DialogsData { courseSeq: number; courseTitle: string; level: number; topics: Topic[] }
    ```
  - `src/data/dialogs.json`: `DialogsData` 형태. `words`는 tagList 원본 보존용(provenance)이며 앱 청킹은 `chunk.ts`가 문장 문자열을 직접 파싱한다.

- [ ] **Step 1: 추출 스크립트 작성**

Create `scripts/extract.py`:
```python
"""server.sqlite 에서 스티브 잡스(course 25) A2(level 2) 대화 22개를 추출해
src/data/dialogs.json 으로 굽는다. 일회성이지만 재생성 가능하도록 커밋한다."""
import sqlite3, json, os

SQLITE = "/Users/namda/sayvoca/conversation-agent/server.sqlite"
COURSE_SEQ = 25
LEVEL = 2
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "dialogs.json")

def words_from_taglist(en, tag_list):
    words = []
    for t in tag_list or []:
        s, e = t.get("s"), t.get("e")
        if s is None or e is None:
            continue
        words.append({"text": en[s:e], "start": s, "end": e})
    return words

def main():
    c = sqlite3.connect(SQLITE)
    course = None
    raw = json.loads(c.execute(
        "SELECT content FROM ResourceFileKR WHERE name='ConversationCourses'").fetchone()[0])
    for co in raw:
        if co["sq"] == COURSE_SEQ:
            course = co
            break
    assert course, "course 25 not found"

    topics = []
    for t in course["to"]:
        topic_seq = t["sq"]
        dseq = topic_seq * 10 + LEVEL
        lo, hi = dseq * 100, dseq * 100 + 99
        rows = c.execute(
            "SELECT seq,data FROM ConversationDialogScriptKR WHERE seq BETWEEN ? AND ? ORDER BY seq",
            (lo, hi)).fetchall()
        scripts = []
        for seq, data in rows:
            d = json.loads(data)
            scripts.append({
                "seq": seq,
                "speaker": d["p"],
                "english": d["en"],
                "translated": d.get("tr", ""),
                "hint": d.get("hint"),
                "words": words_from_taglist(d["en"], d.get("tagList")),
            })
        if scripts:
            topics.append({"topicSeq": topic_seq, "title": t["t"], "partner": t["c"], "scripts": scripts})

    out = {"courseSeq": COURSE_SEQ, "courseTitle": course["t"], "level": LEVEL, "topics": topics}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(topics)} topics -> {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: types.ts 작성**

Create `src/data/types.ts` — 위 Interfaces의 타입 4개 그대로.

- [ ] **Step 3: 추출 실행 및 검증**

Run: `python3 scripts/extract.py`
Expected: `wrote 22 topics -> .../src/data/dialogs.json`

Run: `python3 -c "import json; d=json.load(open('src/data/dialogs.json')); print(len(d['topics']), d['topics'][0]['scripts'][0]['english'], len(d['topics'][0]['scripts'][0]['words']))"`
Expected: `22 Look at this! It connects to a monitor! 8` 정도(단어 수는 문장별 상이).

- [ ] **Step 4: 커밋**

```bash
git add scripts/extract.py src/data/types.ts src/data/dialogs.json
git commit -m "feat: 스티브 잡스 A2 대화 추출 스크립트 + dialogs.json"
```

---

### Task 3: 청커 (단어/규칙) — 순수 함수 + 테스트

**Files:**
- Create: `src/lib/chunk.ts`
- Test: `src/lib/chunk.test.ts`

**Interfaces:**
- Consumes: 없음 (문장 문자열만)
- Produces:
  ```ts
  export interface Chunk { text: string; start: number; end: number }
  export interface Token { text: string; start: number; end: number }
  export function tokenize(sentence: string): Token[]   // 공백 구분, 문장부호는 앞 토큰에 붙음
  export function chunkByWord(sentence: string): Chunk[]
  export function chunkByRule(sentence: string): Chunk[]
  export function chunkSentence(sentence: string, unit: 'word' | 'chunk'): Chunk[]
  ```
- 문장부호 보존이 핵심: `tokenize`가 `\S+`로 잘라 "this!"·"trip?"처럼 부호를 유지한다. 경계 판정은 부호를 뗀 소문자(`norm`)로 하되 표시 텍스트는 원문 토큰 그대로.

- [ ] **Step 1: 실패 테스트 작성**

Create `src/lib/chunk.test.ts`:
```ts
import { describe, it, expect } from 'vitest';
import { tokenize, chunkByWord, chunkByRule, chunkSentence } from './chunk';

describe('tokenize', () => {
  it('문장부호를 앞 토큰에 붙여 보존', () => {
    expect(tokenize('Look at this!').map(t => t.text)).toEqual(['Look', 'at', 'this!']);
  });
});

describe('chunkByWord', () => {
  it('단어 청크(문장부호 포함)', () => {
    expect(chunkByWord('I need a hotel.').map(c => c.text)).toEqual(['I', 'need', 'a', 'hotel.']);
  });
});

describe('chunkByRule', () => {
  it('전치사·to부정사 앞에서 끊는다', () => {
    // want to = 화이트리스트 유지, 'to Rome' 은 전치사 to 앞에서 분리
    expect(chunkByRule('I want to go to Rome').map(c => c.text)).toEqual(['I', 'want to go', 'to Rome']);
  });
  it('고정표현 a lot of 는 쪼개지 않는다', () => {
    expect(chunkByRule('There are a lot of people').map(c => c.text)).toEqual(['There are', 'a lot of people']);
  });
  it('접속사 and 앞에서 끊는다 (문장부호 보존)', () => {
    expect(chunkByRule('Hobbyists and tech fans.').map(c => c.text)).toEqual(['Hobbyists', 'and tech fans.']);
  });
});

describe('chunkSentence', () => {
  it('unit 스위치', () => {
    expect(chunkSentence('I want to go', 'word').length).toBe(4);
    expect(chunkSentence('I want to go', 'chunk').length).toBeLessThan(4);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/chunk.test.ts`
Expected: FAIL ("chunk" 모듈 없음)

- [ ] **Step 3: chunk.ts 구현**

Create `src/lib/chunk.ts`:
```ts
export interface Chunk { text: string; start: number; end: number }
export interface Token { text: string; start: number; end: number }

export function tokenize(sentence: string): Token[] {
  const out: Token[] = [];
  const re = /\S+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(sentence))) out.push({ text: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

// 청크 경계를 '앞에서 끊는' 트리거 단어. 소문자 비교.
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

export function chunkByWord(sentence: string): Chunk[] {
  return tokenize(sentence).map(t => ({ text: t.text, start: t.start, end: t.end }));
}

export function chunkByRule(sentence: string): Chunk[] {
  const tokens = tokenize(sentence);
  const words = tokens.map((t) => norm(t.text));
  // 고정표현 시작 인덱스는 경계로(phraseStart), 중간은 경계 금지(lockedStart).
  // 나머지 로직은 BREAK_BEFORE || phraseStart 에서 flush.
  // 1) 고정표현이 시작되는 토큰 인덱스 → 그 구간은 절대 쪼개지 않도록 표시
  const lockedStart = new Set<number>(); // 이 인덱스에서 새 청크 시작 금지(고정표현 중간)
  const words = tokens.map(t => norm(t.text));
  for (let i = 0; i < tokens.length; i++) {
    for (const phrase of FIXED_PHRASES) {
      const parts = phrase.split(' ');
      if (words.slice(i, i + parts.length).join(' ') === phrase) {
        for (let k = i + 1; k < i + parts.length; k++) lockedStart.add(k); // 중간 토큰은 경계 금지
        break;
      }
    }
  }

  // 2) 경계 결정: BREAK_BEFORE 트리거면서 고정표현 중간이 아니면 새 청크 시작
  const chunks: Chunk[] = [];
  let cur: Token[] = [];
  const flush = () => {
    if (!cur.length) return;
    chunks.push({ text: cur.map(t => t.text).join(' '), start: cur[0].start, end: cur[cur.length - 1].end });
    cur = [];
  };
  for (let i = 0; i < tokens.length; i++) {
    const startsNewChunk = i > 0 && BREAK_BEFORE.has(words[i]) && !lockedStart.has(i);
    if (startsNewChunk) flush();
    cur.push(tokens[i]);
  }
  flush();
  return chunks;
}

export function chunkSentence(sentence: string, unit: 'word' | 'chunk'): Chunk[] {
  return unit === 'word' ? chunkByWord(sentence) : chunkByRule(sentence);
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/chunk.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/lib/chunk.ts src/lib/chunk.test.ts
git commit -m "feat: 청커(단어/규칙) 순수 함수 + 테스트"
```

---

### Task 4: 노출 스케줄 — 순수 함수 + 테스트

**Files:**
- Create: `src/lib/reveal.ts`
- Test: `src/lib/reveal.test.ts`

**Interfaces:**
- Consumes: `Chunk` from `src/lib/chunk.ts`
- Produces:
  ```ts
  export interface RevealSettings { windowSize: number; baseMsPerWord: number; minDwellMs: number }
  export interface RevealStep { index: number; showAt: number; hideAt: number }
  export function dwellMs(chunk: Chunk, s: RevealSettings): number
  export function buildRevealSchedule(chunks: Chunk[], s: RevealSettings): { steps: RevealStep[]; totalMs: number }
  ```

- [ ] **Step 1: 실패 테스트 작성**

Create `src/lib/reveal.test.ts`:
```ts
import { describe, it, expect } from 'vitest';
import { buildRevealSchedule, dwellMs } from './reveal';
import type { Chunk } from './chunk';

const ch = (text: string): Chunk => ({ text, start: 0, end: text.length });
const S = { windowSize: 1, baseMsPerWord: 100, minDwellMs: 300 };

describe('dwellMs', () => {
  it('단어 수 × 기본속도, 최소값 보장', () => {
    expect(dwellMs(ch('to Rome'), S)).toBe(300); // 2*100=200 < 300 → 300
    expect(dwellMs(ch('one two three four'), S)).toBe(400); // 4*100=400
  });
});

describe('buildRevealSchedule', () => {
  it('showAt 은 앞 청크 dwell 누적', () => {
    const chunks = [ch('a'), ch('b'), ch('c')]; // 각 dwell 300
    const { steps, totalMs } = buildRevealSchedule(chunks, S);
    expect(steps.map(s => s.showAt)).toEqual([0, 300, 600]);
    expect(totalMs).toBe(900);
  });
  it('windowSize=1 이면 다음 청크 등장 시 이전 청크 꺼짐', () => {
    const chunks = [ch('a'), ch('b'), ch('c')];
    const { steps } = buildRevealSchedule(chunks, S);
    expect(steps[0].hideAt).toBe(300); // b 등장 시 a off
    expect(steps[2].hideAt).toBe(900); // 마지막은 totalMs 에 off
  });
  it('windowSize=2 이면 두 청크 뒤에 꺼짐', () => {
    const chunks = [ch('a'), ch('b'), ch('c')];
    const { steps } = buildRevealSchedule(chunks, { ...S, windowSize: 2 });
    expect(steps[0].hideAt).toBe(600); // c(index2) 등장 시 a off
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `npx vitest run src/lib/reveal.test.ts`
Expected: FAIL (모듈 없음)

- [ ] **Step 3: reveal.ts 구현**

Create `src/lib/reveal.ts`:
```ts
import type { Chunk } from './chunk';

export interface RevealSettings { windowSize: number; baseMsPerWord: number; minDwellMs: number }
export interface RevealStep { index: number; showAt: number; hideAt: number }

export function dwellMs(chunk: Chunk, s: RevealSettings): number {
  const wordCount = chunk.text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(s.minDwellMs, wordCount * s.baseMsPerWord);
}

export function buildRevealSchedule(chunks: Chunk[], s: RevealSettings): { steps: RevealStep[]; totalMs: number } {
  const windowSize = Math.max(1, Math.floor(s.windowSize)); // 방어: 최소 1
  const showAt: number[] = [];
  let acc = 0;
  for (let i = 0; i < chunks.length; i++) {
    showAt.push(acc);
    acc += dwellMs(chunks[i], s);
  }
  const totalMs = acc;
  const steps: RevealStep[] = chunks.map((_, i) => {
    const hideIdx = i + windowSize; // 이 인덱스가 등장하면 i 는 꺼진다
    const hideAt = hideIdx < chunks.length ? showAt[hideIdx] : totalMs;
    return { index: i, showAt: showAt[i], hideAt };
  });
  return { steps, totalMs };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/lib/reveal.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/lib/reveal.ts src/lib/reveal.test.ts
git commit -m "feat: 노출 스케줄 순수 함수 + 테스트"
```

---

### Task 5: useSlidingReveal 훅 (generation guard)

**Files:**
- Create: `src/hooks/useSlidingReveal.ts`
- Test: `src/hooks/useSlidingReveal.test.ts`

**Interfaces:**
- Consumes: `buildRevealSchedule`, `RevealSettings` from `src/lib/reveal.ts`, `Chunk` from `src/lib/chunk.ts`
- Produces:
  ```ts
  export function useSlidingReveal(): {
    visible: Set<number>;
    play: (chunks: Chunk[], settings: RevealSettings, onDone?: () => void) => void;
    reset: () => void;
  }
  ```
- 설계 근거(Codex 리뷰 반영):
  - `play`는 chunks·settings를 **인자로** 받는다 → 재생 시작 시점에 고정("다음 노출부터 반영" semantics). closure 통한 stale 참조 없음.
  - **generation guard**(`gen` ref): `play`/`reset` 때마다 세대 증가. 각 setTimeout callback은 자기 세대가 최신일 때만 실행 → reset/replay 직후 큐에 남은 옛 콜백은 no-op.
  - `play`·`reset`은 `useCallback([clear])`로 **안정 참조** → 소비 컴포넌트 effect 의존성에 안전하게 넣을 수 있음.

- [ ] **Step 1: 실패 테스트 작성 (fake timer)**

`src/hooks/useSlidingReveal.test.ts` 상단에 jsdom 환경 지정:
```ts
// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSlidingReveal } from './useSlidingReveal';
import type { Chunk } from '../lib/chunk';

const ch = (t: string): Chunk => ({ text: t, start: 0, end: t.length });
const S = { windowSize: 1, baseMsPerWord: 100, minDwellMs: 300 };

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('useSlidingReveal', () => {
  it('스케줄대로 노출·소멸하고 onDone 호출', () => {
    const onDone = vi.fn();
    const { result } = renderHook(() => useSlidingReveal());
    act(() => result.current.play([ch('a'), ch('b')], S, onDone));
    act(() => vi.advanceTimersByTime(0));
    expect([...result.current.visible]).toEqual([0]);   // a 노출
    act(() => vi.advanceTimersByTime(300));
    expect([...result.current.visible]).toEqual([1]);   // b 노출, a 소멸(window=1)
    act(() => vi.advanceTimersByTime(400));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('reset 후 옛 타이머는 visible 을 건드리지 않는다 (generation guard)', () => {
    const { result } = renderHook(() => useSlidingReveal());
    act(() => result.current.play([ch('a'), ch('b')], S));
    act(() => result.current.reset());
    act(() => vi.advanceTimersByTime(1000));
    expect([...result.current.visible]).toEqual([]);
  });
});
```

- [ ] **Step 2: jsdom·testing-library 설치 후 테스트 실패 확인**

```bash
npm install -D jsdom @testing-library/react @testing-library/dom
```
`vitest.config.ts`의 `include`를 `['src/**/*.test.ts', 'src/**/*.test.tsx']`로 확장(현재 .ts만).

Run: `npx vitest run src/hooks/useSlidingReveal.test.ts`
Expected: FAIL (모듈 없음)

- [ ] **Step 3: 훅 구현 (generation guard, cleanup 필수)**

Create `src/hooks/useSlidingReveal.ts`:
```ts
import { useCallback, useEffect, useRef, useState } from 'react';
import { buildRevealSchedule, type RevealSettings } from '../lib/reveal';
import type { Chunk } from '../lib/chunk';

export function useSlidingReveal() {
  const [visible, setVisible] = useState<Set<number>>(new Set());
  const timers = useRef<number[]>([]);
  const gen = useRef(0);

  const clear = useCallback(() => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }, []);

  const play = useCallback((chunks: Chunk[], settings: RevealSettings, onDone?: () => void) => {
    clear();
    const myGen = ++gen.current;
    setVisible(new Set());
    const { steps, totalMs } = buildRevealSchedule(chunks, settings);
    for (const step of steps) {
      timers.current.push(window.setTimeout(() => {
        if (gen.current !== myGen) return;
        setVisible((prev) => new Set(prev).add(step.index));
      }, step.showAt));
      timers.current.push(window.setTimeout(() => {
        if (gen.current !== myGen) return;
        setVisible((prev) => { const n = new Set(prev); n.delete(step.index); return n; });
      }, step.hideAt));
    }
    timers.current.push(window.setTimeout(() => {
      if (gen.current !== myGen) return;
      onDone?.();
    }, totalMs + 50));
  }, [clear]);

  const reset = useCallback(() => { gen.current++; clear(); setVisible(new Set()); }, [clear]);

  useEffect(() => clear, [clear]); // 언마운트 시 타이머 정리
  return { visible, play, reset };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npx vitest run src/hooks/useSlidingReveal.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/hooks/useSlidingReveal.ts src/hooks/useSlidingReveal.test.ts vitest.config.ts package.json package-lock.json
git commit -m "feat: useSlidingReveal 훅 (generation guard) + 테스트"
```

---

### Task 6: DialogBubble 컴포넌트

**Files:**
- Create: `src/components/DialogBubble.tsx`
- Create: `src/components/DialogBubble.css`

**Interfaces:**
- Consumes: `Chunk`, `RevealState.visible`
- Produces:
  ```tsx
  export function DialogBubble(props: {
    speaker: 'A' | 'B'; chunks: Chunk[]; visible: Set<number>;
  }): JSX.Element
  ```

- [ ] **Step 1: 컴포넌트 구현**

핵심: 모든 청크를 자연스러운 흐름의 span 으로 배치하고, visible 집합에 없으면 `visibility:hidden`(자리 유지·글자 숨김) → "빈 공백 + 길이 노출 + 위치 맥락".

Create `src/components/DialogBubble.tsx`:
```tsx
import type { Chunk } from '../lib/chunk';
import './DialogBubble.css';

export function DialogBubble({ speaker, chunks, visible }: {
  speaker: 'A' | 'B'; chunks: Chunk[]; visible: Set<number>;
}) {
  return (
    <div className={`bubble-row ${speaker === 'A' ? 'right' : 'left'}`}>
      <div className="bubble">
        {chunks.map((c, i) => (
          <span key={i} className="chunk" style={{ visibility: visible.has(i) ? 'visible' : 'hidden' }}>
            {c.text}{' '}
          </span>
        ))}
      </div>
    </div>
  );
}
```

Create `src/components/DialogBubble.css`:
```css
.bubble-row { display: flex; margin: 8px 0; }
.bubble-row.left { justify-content: flex-start; }
.bubble-row.right { justify-content: flex-end; }
.bubble {
  max-width: 78%; padding: 12px 16px; border-radius: 16px;
  line-height: 1.9; font-size: 20px; background: #eef1f5;
}
.bubble-row.right .bubble { background: #d9ebff; }
.chunk { white-space: pre; }
```

- [ ] **Step 2: 타입 체크**

Run: `npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add src/components/DialogBubble.tsx src/components/DialogBubble.css
git commit -m "feat: DialogBubble (visibility 기반 슬라이딩 창)"
```

---

### Task 7: 설정 컨텍스트 + 패널

**Files:**
- Create: `src/settings/SettingsContext.tsx`
- Create: `src/components/SettingsPanel.tsx`
- Create: `src/components/SettingsPanel.css`

**Interfaces:**
- Produces:
  ```tsx
  export interface Settings { unit: 'word' | 'chunk'; windowSize: number; baseMsPerWord: number }
  export const DEFAULT_SETTINGS: Settings // { unit:'chunk', windowSize:2, baseMsPerWord:220 }
  export function SettingsProvider(props: { children: React.ReactNode }): JSX.Element
  export function useSettings(): { settings: Settings; setSettings: (s: Settings) => void }
  export function SettingsPanel(): JSX.Element
  ```
- `minDwellMs` 상수는 `reveal` 호출부에서 `300` 고정으로 주입한다(설정 축 아님).

- [ ] **Step 1: 컨텍스트 구현**

Create `src/settings/SettingsContext.tsx`:
```tsx
import { createContext, useContext, useState } from 'react';

export interface Settings { unit: 'word' | 'chunk'; windowSize: number; baseMsPerWord: number }
export const DEFAULT_SETTINGS: Settings = { unit: 'chunk', windowSize: 2, baseMsPerWord: 220 };

const Ctx = createContext<{ settings: Settings; setSettings: (s: Settings) => void } | null>(null);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  return <Ctx.Provider value={{ settings, setSettings }}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useSettings must be used within SettingsProvider');
  return v;
}
```

- [ ] **Step 2: 패널 구현**

Create `src/components/SettingsPanel.tsx`:
```tsx
import { useSettings } from '../settings/SettingsContext';
import './SettingsPanel.css';

export function SettingsPanel() {
  const { settings, setSettings } = useSettings();
  return (
    <div className="settings-panel">
      <label>
        노출 단위
        <select value={settings.unit}
          onChange={(e) => setSettings({ ...settings, unit: e.target.value as 'word' | 'chunk' })}>
          <option value="word">단어</option>
          <option value="chunk">청크</option>
        </select>
      </label>
      <label>
        창 크기 N: {settings.windowSize}
        <input type="range" min={1} max={5} value={settings.windowSize}
          onChange={(e) => setSettings({ ...settings, windowSize: Number(e.target.value) })} />
      </label>
      <label>
        속도(ms/단어): {settings.baseMsPerWord}
        <input type="range" min={80} max={500} step={20} value={settings.baseMsPerWord}
          onChange={(e) => setSettings({ ...settings, baseMsPerWord: Number(e.target.value) })} />
      </label>
    </div>
  );
}
```

Create `src/components/SettingsPanel.css`:
```css
.settings-panel { display: flex; gap: 20px; flex-wrap: wrap; padding: 12px 16px;
  background: #fafafa; border: 1px solid #eee; border-radius: 12px; font-size: 14px; }
.settings-panel label { display: flex; flex-direction: column; gap: 4px; }
```

- [ ] **Step 3: 타입 체크 + 커밋**

Run: `npx tsc --noEmit`
Expected: 에러 없음

```bash
git add src/settings/SettingsContext.tsx src/components/SettingsPanel.tsx src/components/SettingsPanel.css
git commit -m "feat: 설정 컨텍스트 + 실시간 패널"
```

---

### Task 8: ReadingSession (대화 순회·자동 진행·리플레이)

**Files:**
- Create: `src/components/ReadingSession.tsx`
- Create: `src/components/ReadingSession.css`

**Interfaces:**
- Consumes: `Topic`, `useSettings`, `chunkSentence`+`Chunk`, `useSlidingReveal`, `DialogBubble`
- Produces:
  ```tsx
  export function ReadingSession(props: { topic: Topic; onFinish: () => void }): JSX.Element
  ```
- 동작·설계 근거(Codex 리뷰 반영):
  - 재생은 **`useEffect([index, runId, finished, play])`**에서 `play(chunks, settings)`를 명시 호출. autoStart 미사용 → 단일 스크립트도 `runId` 증가로 리플레이 재생 보장.
  - 설정은 `settingsRef`로 읽어 **effect 의존성에서 제외** → 설정 변경이 현재 문장을 재시작시키지 않음(다음 문장/다시보기부터 반영). play에 넘긴 chunks·settings는 시작 시점 스냅샷.
  - 현재 문장 chunks는 `currentChunks` state에 고정 저장 → 재생 중 unit이 바뀌어도 hook과 DialogBubble이 **같은 chunks**를 봐서 인덱스 desync 없음.
  - **GAP 진행 타이머는 `gapTimer` ref로 추적**하고 effect cleanup·replay에서 정리 → stale advance 방지.
  - `visible`을 effect 의존성에 넣지 않기 위해 `play`/`reset`만 구조분해(안정 참조).

- [ ] **Step 1: 컴포넌트 구현**

Create `src/components/ReadingSession.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { chunkSentence, type Chunk } from '../lib/chunk';
import { useSlidingReveal } from '../hooks/useSlidingReveal';
import { useSettings } from '../settings/SettingsContext';
import { DialogBubble } from './DialogBubble';
import './ReadingSession.css';

const MIN_DWELL_MS = 300;
const GAP_MS = 400;

export function ReadingSession({ topic, onFinish }: { topic: Topic; onFinish: () => void }) {
  const { settings } = useSettings();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const [index, setIndex] = useState(0);
  const [runId, setRunId] = useState(0);   // 같은 index 재생 강제(리플레이)용
  const [finished, setFinished] = useState(false);
  const [currentChunks, setCurrentChunks] = useState<Chunk[]>([]);

  const { visible, play, reset } = useSlidingReveal();
  const gapTimer = useRef<number | null>(null);

  useEffect(() => {
    if (finished) return;
    const script = topic.scripts[index];
    if (!script) return;
    const s = settingsRef.current; // 시작 시점 설정 스냅샷
    const chunks = chunkSentence(script.english, s.unit);
    setCurrentChunks(chunks);
    play(
      chunks,
      { windowSize: s.windowSize, baseMsPerWord: s.baseMsPerWord, minDwellMs: MIN_DWELL_MS },
      () => {
        if (index + 1 >= topic.scripts.length) { setFinished(true); return; }
        gapTimer.current = window.setTimeout(() => setIndex((i) => i + 1), GAP_MS);
      },
    );
    return () => { if (gapTimer.current) { window.clearTimeout(gapTimer.current); gapTimer.current = null; } };
  }, [index, runId, finished, topic, play]);

  const replay = () => {
    if (gapTimer.current) { window.clearTimeout(gapTimer.current); gapTimer.current = null; }
    reset();
    setFinished(false);
    setIndex(0);
    setRunId((r) => r + 1); // index 가 이미 0이어도 effect 재실행
  };

  return (
    <div className="session">
      <div className="chat">
        {topic.scripts.slice(0, index + 1).map((s, i) => (
          <DialogBubble
            key={s.seq}
            speaker={s.speaker}
            chunks={i === index ? currentChunks : chunkSentence(s.english, settings.unit)}
            visible={i === index && !finished ? visible : new Set<number>()}
          />
        ))}
      </div>
      {finished && (
        <div className="session-actions">
          <button onClick={replay}>다시 보기</button>
          <button className="primary" onClick={onFinish}>문제 풀기</button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: CSS**

Create `src/components/ReadingSession.css`:
```css
.session { display: flex; flex-direction: column; gap: 16px; }
.chat { min-height: 320px; display: flex; flex-direction: column; }
.session-actions { display: flex; gap: 12px; justify-content: center; }
.session-actions button { padding: 10px 20px; border-radius: 10px; border: 1px solid #ccc; cursor: pointer; font-size: 15px; }
.session-actions button.primary { background: #2b7cff; color: #fff; border-color: #2b7cff; }
```

- [ ] **Step 3: 타입 체크 + 커밋**

Run: `npx tsc --noEmit`
Expected: 에러 없음

```bash
git add src/components/ReadingSession.tsx src/components/ReadingSession.css
git commit -m "feat: ReadingSession 대화 순회·자동 진행·리플레이"
```

---

### Task 9: 퀴즈 데이터 저작 + Quiz 컴포넌트

**Files:**
- Create: `src/data/quizzes.json`
- Create: `src/data/quizTypes.ts`
- Create: `src/components/Quiz.tsx`
- Create: `src/components/Quiz.css`

**Interfaces:**
- Produces:
  ```ts
  // quizTypes.ts
  export interface QuizQuestion { question: string; options: string[]; answerIndex: number; explanation: string }
  export type QuizMap = Record<number, QuizQuestion[]> // key = topicSeq
  ```
  ```tsx
  export function Quiz(props: { topicSeq: number; onDone: () => void }): JSX.Element
  ```

- [ ] **Step 1: 퀴즈 저작**

`src/data/dialogs.json`의 22개 토픽 각각을 읽고, 대화 내용이해 한국어 MCQ 2문항씩 저작한다.
각 문항 옵션 4개, `answerIndex`는 정답 위치, `explanation`은 한 줄 해설.

예시(topicSeq 2501, "차고에서 만난 혁명" — 워즈니악이 컴퓨터를 만들었고 잡스가 회사 차리자고 설득):
```json
{
  "2501": [
    {
      "question": "B(워즈니악)가 만든 것은 무엇인가?",
      "options": ["모니터에 연결되는 컴퓨터", "새 자동차", "게임기", "라디오"],
      "answerIndex": 0,
      "explanation": "B는 모니터에 연결되어 화면에 글자가 나오는 컴퓨터를 몇 달간 만들었다."
    },
    {
      "question": "A(잡스)가 마지막에 제안한 것은?",
      "options": ["컴퓨터를 팔지 말자", "회사를 차리자", "취미로만 하자", "가격을 올리자"],
      "answerIndex": 1,
      "explanation": "A는 시장이 있다며 'Let's start a company'라고 회사 창업을 제안했다."
    }
  ]
}
```
나머지 21개 토픽도 같은 스키마로 채운다. (구현 시 dialogs.json 을 실제로 읽고 저작할 것 — 위는 형식 예시)

- [ ] **Step 2: quizTypes.ts 작성**

Create `src/data/quizTypes.ts` — 위 Interfaces의 타입 그대로.

- [ ] **Step 3: Quiz 컴포넌트 구현**

Create `src/components/Quiz.tsx`:
```tsx
import { useState } from 'react';
import quizzes from '../data/quizzes.json';
import type { QuizMap } from '../data/quizTypes';
import './Quiz.css';

const QUIZ = quizzes as unknown as QuizMap;

export function Quiz({ topicSeq, onDone }: { topicSeq: number; onDone: () => void }) {
  const questions = QUIZ[topicSeq] ?? [];
  const [picked, setPicked] = useState<(number | null)[]>(() => questions.map(() => null));

  const answeredAll = picked.every((p) => p !== null);
  const correct = picked.filter((p, i) => p === questions[i].answerIndex).length;

  return (
    <div className="quiz">
      {questions.map((q, qi) => (
        <div key={qi} className="quiz-q">
          <p className="quiz-question">{qi + 1}. {q.question}</p>
          {q.options.map((opt, oi) => {
            const chosen = picked[qi] === oi;
            const revealed = picked[qi] !== null;
            const isAnswer = oi === q.answerIndex;
            const cls = revealed ? (isAnswer ? 'correct' : chosen ? 'wrong' : '') : '';
            return (
              <button key={oi} className={`quiz-opt ${cls}`} disabled={picked[qi] !== null}
                onClick={() => setPicked((arr) => arr.map((v, i) => (i === qi ? oi : v)))}>
                {opt}
              </button>
            );
          })}
          {picked[qi] !== null && <p className="quiz-explain">{q.explanation}</p>}
        </div>
      ))}
      {answeredAll && (
        <div className="quiz-result">
          <p>{questions.length}문제 중 {correct}개 정답</p>
          <button className="primary" onClick={onDone}>토픽 목록으로</button>
        </div>
      )}
    </div>
  );
}
```

Create `src/components/Quiz.css`:
```css
.quiz { display: flex; flex-direction: column; gap: 20px; }
.quiz-question { font-weight: 600; margin-bottom: 8px; }
.quiz-opt { display: block; width: 100%; text-align: left; padding: 10px 14px; margin: 6px 0;
  border: 1px solid #ccc; border-radius: 10px; background: #fff; cursor: pointer; }
.quiz-opt.correct { background: #d7f5dd; border-color: #34a853; }
.quiz-opt.wrong { background: #fbe0e0; border-color: #ea4335; }
.quiz-explain { font-size: 14px; color: #555; margin-top: 6px; }
.quiz-result { text-align: center; }
.quiz-result .primary { background: #2b7cff; color: #fff; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; }
```

- [ ] **Step 4: 타입 체크 + 커밋**

Run: `npx tsc --noEmit` (json import 위해 tsconfig `resolveJsonModule` 확인, Vite 기본 활성)
Expected: 에러 없음

```bash
git add src/data/quizzes.json src/data/quizTypes.ts src/components/Quiz.tsx src/components/Quiz.css
git commit -m "feat: 퀴즈 데이터 + Quiz 컴포넌트"
```

---

### Task 10: App 내비게이션 + 조립

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/main.tsx` (SettingsProvider 래핑)
- Create: `src/App.css`
- Create: `src/components/TopicList.tsx`

**Interfaces:**
- Consumes: 전 태스크 전부
- Produces: 화면 상태기계 `'topics' | 'session' | 'quiz'`

- [ ] **Step 1: TopicList 구현**

Create `src/components/TopicList.tsx`:
```tsx
import dialogs from '../data/dialogs.json';
import type { DialogsData } from '../data/types';

const DATA = dialogs as unknown as DialogsData;

export function TopicList({ onPick }: { onPick: (topicSeq: number) => void }) {
  return (
    <div className="topic-list">
      <h1>{DATA.courseTitle} <small>(A2)</small></h1>
      <ul>
        {DATA.topics.map((t) => (
          <li key={t.topicSeq}>
            <button onClick={() => onPick(t.topicSeq)}>{t.title} <span>· {t.partner}</span></button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: App 상태기계 구현**

Modify `src/App.tsx` (전체 교체):
```tsx
import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData } from './data/types';
import { TopicList } from './components/TopicList';
import { ReadingSession } from './components/ReadingSession';
import { Quiz } from './components/Quiz';
import { SettingsPanel } from './components/SettingsPanel';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('topics');
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const topic = DATA.topics.find((t) => t.topicSeq === topicSeq) ?? null;

  return (
    <div className="app">
      {screen !== 'topics' && (
        <header className="app-header">
          <button onClick={() => setScreen('topics')}>← 목록</button>
          <SettingsPanel />
        </header>
      )}
      <main className="app-main">
        {screen === 'topics' && (
          <TopicList onPick={(s) => { setTopicSeq(s); setScreen('session'); }} />
        )}
        {screen === 'session' && topic && (
          <ReadingSession key={topic.topicSeq} topic={topic} onFinish={() => setScreen('quiz')} />
        )}
        {screen === 'quiz' && topic && (
          <Quiz topicSeq={topic.topicSeq} onDone={() => setScreen('topics')} />
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: main.tsx 에 SettingsProvider 래핑**

Modify `src/main.tsx` — `<App/>`를 `<SettingsProvider><App/></SettingsProvider>`로 감싸고 import 추가.

- [ ] **Step 4: App.css**

Create `src/App.css`:
```css
.app { max-width: 720px; margin: 0 auto; padding: 20px; font-family: system-ui, sans-serif; }
.app-header { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.app-header > button { align-self: flex-start; background: none; border: none; cursor: pointer; color: #2b7cff; font-size: 15px; }
.topic-list ul { list-style: none; padding: 0; }
.topic-list li button { width: 100%; text-align: left; padding: 14px 16px; margin: 6px 0;
  border: 1px solid #e3e3e3; border-radius: 12px; background: #fff; cursor: pointer; font-size: 16px; }
.topic-list li span { color: #888; font-size: 13px; }
```

- [ ] **Step 5: 빌드 + 타입 체크**

Run: `npx tsc --noEmit && npm run build`
Expected: 에러 없음, dist 생성

- [ ] **Step 6: 커밋**

```bash
git add src/App.tsx src/main.tsx src/App.css src/components/TopicList.tsx
git commit -m "feat: App 내비게이션 + 전체 조립"
```

---

### Task 11: 수동 검증 (E2E 체감)

**Files:** 없음 (실행 확인)

- [ ] **Step 1: 개발 서버 실행**

Run: `npm run dev`
브라우저에서 확인:
1. 스티브 잡스 코스 토픽 22개 목록 표시
2. 토픽 선택 → 말풍선이 문장 크기로 뜨고, 청크가 창(N=2)만큼 슬라이딩하며 노출·소멸
3. 설정에서 단위(단어↔청크)·N·속도 조절 → **현재 문장은 그대로, 다음 문장부터 반영**
4. 대화 끝 → "다시 보기"/"문제 풀기" 버튼. **다시 보기 시 처음부터 정상 재생**(스크립트 1개짜리 토픽도 재생되는지 확인)
5. **재생 중 목록으로 나갔다가 다른 토픽 진입 시** 이전 타이머가 새 화면을 건드리지 않는지 확인(stale timer)
6. 문제 풀기 → 2문항 MCQ, 답 선택 시 정답·해설 피드백 → "토픽 목록으로"

- [ ] **Step 2: 전체 테스트 통과 확인**

Run: `npm test`
Expected: chunk(6) + reveal(4) + useSlidingReveal(2) 통과

- [ ] **Step 3: 최종 커밋 (필요 시)**

```bash
git add -A && git commit -m "chore: 리딩 모드 POC 검증 완료" || echo "nothing to commit"
```

---

## Self-Review 결과

- **Spec coverage:** 노출 메커니즘(Task 6,4,5,8), 실험 축 3개(Task 7), 청킹 단어/규칙(Task 3), 콘텐츠 22개 추출(Task 2), 한국어 MCQ 2문항(Task 9), 다시 보기(Task 8), 코스/토픽 선택(Task 10) — 모두 태스크 존재.
- **Placeholder scan:** Task 9의 퀴즈 저작은 dialogs.json 실제 내용 의존이라 형식 예시 + 스키마 제공, 구현 시 22개 저작. 그 외 코드 스텝은 전부 실제 코드.
- **Type consistency:** `Chunk`(chunk.ts) → reveal/hook/bubble 일관, `Settings`/`RevealSettings` 분리(설정 축 3개 + minDwellMs 상수 주입), `DialogsData`/`Topic`/`Script`/`Token`(chunk.ts는 자체 Token 정의) 일관, `QuizMap` key=topicSeq 일관.

## Codex 리뷰 반영 (2026-07-03)

- **타이머 race:** hook에 generation guard 도입, `play(chunks, settings)` 인자형으로 stale closure 제거, `reset` 세대 증가로 옛 콜백 무력화 (Task 5).
- **GAP 진행 타이머 누수:** `gapTimer` ref 추적 + effect cleanup·replay 정리 (Task 8).
- **단일 스크립트 리플레이 불발:** autoStart 폐기, `runId` 토큰으로 명시 재생 (Task 8).
- **설정 변경 semantics 확정:** 현재 문장 미영향, 다음 문장/다시보기부터 반영. `settingsRef` + `currentChunks` 고정 (Global Constraints, Task 8).
- **문장부호 유실:** tagList 대신 문장 문자열 직접 토큰화(`\S+`), 부호를 앞 토큰에 보존 (Task 3).
- **방어 코드:** `windowSize` 최소 1 클램프 (Task 4).
- **테스트 보강:** 가장 위험한 hook에 fake-timer 테스트 추가 (Task 5).
- **미반영(POC 범위 밖):** `visibility:hidden`의 스크린리더 처리(접근성), 반응형 정밀 검증 — POC 체험 도구 범위에서 제외.
