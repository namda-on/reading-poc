# CLAUDE.md

## Project overview

리스닝이 불가능한 환경에서도 같은 회화 콘텐츠로 훈련하는 **리딩 모드 POC**.
리스닝의 "실시간 처리"를 소리 없이 재현한다 — 문장 크기만큼 확보된 말풍선 위를 N개짜리 창(window)이 청크의 실제 위치를 따라 슬라이딩하며 노출하고, 지나간/미래 청크는 빈 공백으로 남겨 되돌아가기·미리보기를 차단한다. 대화가 끝나면 한국어 객관식 1문항을 바텀시트로 푼다.

세션 시작 화면에서 **리딩 / 리스닝** 모드를 고른다. 리스닝은 같은 대화를 실제 TTS 음성(speech.epop.ai)으로 재생하되 텍스트는 완전히 숨긴다(순수 듣기). 두 모드 모두 끝나면 같은 퀴즈로 이어진다.

**주관적 체험용 프로토타입**이다. 정량 로깅·서버·백엔드 없음. 실험 축은 노출 단위(단어/청크)·창 크기 N·속도(ms/음절).

설계·구현 계획 문서: `docs/superpowers/specs/`, `docs/superpowers/plans/`.

## Commands

```bash
npm run dev            # 개발 서버
npm run build          # tsc -b && vite build
npm test               # vitest (chunk / reveal / useSlidingReveal)
python3 scripts/extract.py   # 대화 데이터(dialogs.json) 재생성
```

## Directory map

- `src/lib/chunk.ts` — 문장 → 청크 분할(순수 함수). 단어 모드 / 규칙 모드.
- `src/lib/reveal.ts` — 노출 스케줄(순수 함수). 음절 기반 dwell 계산.
- `src/hooks/useSlidingReveal.ts` — 스케줄을 타이머로 구동(generation guard).
- `src/components/` — `StoryList`(첫 화면) · `TopicList` · `SessionStart`(모드 선택 시작 화면) · `ReadingSession`(리딩 재생) · `ListeningSession`(리스닝 오디오 재생, 텍스트 숨김) · `DialogBubble` · `SettingsPanel` · `QuizSheet`/`Quiz`.
- `src/settings/SettingsContext.tsx` — 설정 상태 + localStorage.
- `src/lib/progress.ts` — 푼 토픽 localStorage 저장.
- `src/data/` — `dialogs.json`(생성물, 커밋됨) · `quizzes.json`(수기 저작) · `types.ts` · `quizTypes.ts`.
- `scripts/extract.py` — 외부 sqlite에서 대화 추출.

화면 흐름: 스토리 선택 → 에피소드(토픽) 목록 → 시작 화면(모드 선택) → 세션(리딩/리스닝 재생) → 퀴즈(바텀시트). `App.tsx`가 상태기계로 관리(`mode`·`playing` 상태).

## 데이터 파이프라인

`dialogs.json`은 커밋된 생성물이자 런타임의 유일한 소스다(sqlite 없이도 앱은 동작). 재생성할 때만 `scripts/extract.py`를 쓰고, **손으로 편집하지 말 것**.

- 출처: bi의 `server.sqlite` (이 레포 밖). 경로는 `READING_POC_SQLITE` 환경변수 또는 CLI 인자로 지정. 없으면 명확한 에러로 종료한다.
  - 필수 테이블: `ConversationDialogScriptKR`(스크립트 + `voiceInfos` 해시), `ResourceFileKR`의 `ConversationCourses`(코스/토픽 + 대화별 `di[].h` = dialogHash). 사전 전용 오래된 export에는 대화 테이블이 없으니 **최신 export를 쓸 것**.
- 포함 코스: `INCLUDE = [25(잡스), 17(투자), 2(뉴욕여행)]`, 레벨 A2(=2) 고정.
- 각 에피소드는 **도입부 4턴(`MAX_SCRIPTS`)만** 사용 — 리딩 분량을 짧게.
- 단어 경계는 tagList가 아니라 문장 문자열을 직접 파싱(문장부호 보존).
- **리스닝 오디오 URL**을 스크립트마다 `audioUrl`로 구워 넣는다. 형식:
  `https://speech.epop.ai/conversation/tts/{dialogSeq:06d}-{dialogHash}/{voiceType}/{scriptIdx:02d}.{voiceHash}.ogg`
  (dialogSeq = topicSeq×10+level, scriptIdx = scriptSeq%100, voiceType = `voiceInfos`의 non-null 인덱스 폴더명, voiceHash = 그 해시). CDN은 인증 없는 공개 접근이라 런타임에서 바로 재생된다.

`quizzes.json`은 `topicSeq`(코스별로 유니크)를 키로 하는 수기 저작 데이터. 대화당 1문항.

## Conventions

- 주석·UI 문구는 한국어. 식별자만 영어.
- 순수 로직(`chunk.ts`, `reveal.ts`, hook)은 TDD. `src/**/*.test.ts(x)`.
- 생성물 fixture(`dialogs.json`)도 커밋한다(런타임 sqlite 의존 0).
- 음절 계산은 `syllable` 패키지.

## Quirks / 주의

- **노출 규칙**: 청크 i는 (i+N)번째 청크가 등장하는 순간 사라진다(항상 최근 N개 유지). dwell = `max(300ms, 음절수 × 속도설정)`. 사라짐은 하드컷이 아니라 opacity 450ms 페이드(자리는 유지). 상세는 `reveal.ts`.
- **퀴즈 정답은 반드시 노출되는 턴(현재 4턴) 안에 있어야 한다.** `MAX_SCRIPTS`를 줄이면 정답이 잘린 문제가 생기므로 해당 퀴즈를 재작성해야 한다. 재생성 후 `dialogs.json`에 정답 근거 문구가 있는지 확인할 것.
- **localStorage 키**: `reading-poc:settings`(설정) · `reading-poc:solved`(푼 토픽). 기존 저장값이 있으면 기본값보다 우선하므로, 새 기본값 확인 시 저장소를 비운다.
- **모드 선택·다시 듣기**: 토픽 진입 시 `SessionStart`(모드 선택 + 리딩 설정)를 거쳐 재생. 리딩 노출 설정은 리딩 모드에서만 노출. 퀴즈의 "다시 듣기"는 시작 화면을 건너뛰고 **같은 모드로 즉시** 처음부터 재생(`sessionRun` 증가로 세션 리마운트).
- **리스닝 재생**: 문장 단위 오디오를 순차 재생, `ended`(또는 `error`)에 다음으로. 자동재생은 시작 버튼 클릭(사용자 제스처) 직후라 허용된다. 텍스트는 숨기고 재생 중 말풍선에만 웨이브 인디케이터를 표시.
- **Vercel 배포**: 커밋 author 이메일이 GitHub 계정(namda-on)에 등록된 주소여야 배포가 식별된다. 이 레포는 `user.email = namda1571@gmail.com`으로 설정돼 있다.
- **화자 표시는 A/B**, 에피소드 제목은 "Episode N"만 — 제목·상대역이 주제를 노출해 문제가 쉬워지는 것을 막기 위함.
