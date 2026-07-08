# CLAUDE.md

## Project overview

리스닝이 불가능한 환경에서도 같은 회화 콘텐츠로 훈련하는 **리딩 모드 POC**.
리스닝의 "실시간 처리"를 소리 없이 재현한다 — 문장 크기만큼 확보된 말풍선 위를 N개짜리 창(window)이 청크의 실제 위치를 따라 슬라이딩하며 노출하고, 지나간/미래 청크는 빈 공백으로 남겨 되돌아가기·미리보기를 차단한다. 대화가 끝나면 한국어 객관식 1문항을 바텀시트로 푼다.

세션 시작 화면에서 **리딩 / 리스닝 / 전광판 / 고정** 모드를 고른다. 리스닝은 같은 대화를 실제 TTS 음성(speech.epop.ai)으로 재생하되 텍스트는 완전히 숨긴다(순수 듣기). 전광판은 같은 말풍선 레이아웃에서 각 문장이 오른쪽→왼쪽으로 흘러 지나가는 LED 전광판식 노출이다. 고정은 시선을 한 곳에 둔 채 화면 중앙에서 단어/청크가 제자리 교체되는 RSVP식 노출이다(시선 이동 없이 읽기 비교용). 모든 모드가 끝나면 같은 퀴즈로 이어진다.

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
- `src/components/` — `StoryList`(첫 화면) · `TopicList` · `SessionStart`(모드 선택 시작 화면) · `ReadingSession`(리딩 재생) · `ListeningSession`(리스닝 오디오 재생, 텍스트 숨김) · `MarqueeSession`(전광판식 가로 흐름) · `FixedSession`(시선 고정 RSVP) · `DialogBubble` · `SettingsPanel` · `QuizSheet`(문제 바텀시트) · `Quiz`(객관식)/`ArrangeQuiz`(단어 배열)/`DictationQuiz`(받아쓰기).
- `src/settings/SettingsContext.tsx` — 설정 상태 + localStorage.
- `src/lib/progress.ts` — 푼 토픽 localStorage 저장.
- `src/lib/keySentence.ts` — 배열·받아쓰기 문제에 쓸 '핵심 1문장' 선택. 스크립트를 문장 단위로 쪼개(항상 단일 문장), 퀴즈 힌트(질문·정답·해설)와 한국어 글자 바이그램 겹침이 가장 큰 문장을 고른다(정답 근거 문장). 힌트/겹침이 없으면 3~9단어 중 가장 긴 문장.
- `src/lib/quizHint.ts` — `topicSeq`의 퀴즈 질문·정답·해설을 합친 한국어 힌트(핵심 문장 선정용).
- `src/data/` — `dialogs.json`(생성물, 커밋됨) · `quizzes.json`(수기 저작) · `types.ts` · `quizTypes.ts`.
- `scripts/extract.py` — 외부 sqlite에서 대화 추출.
- `public/listening-pingpong.html` — **별도** 리스닝 핑퐁 프로토타입(자체 완결형 HTML, 저작 대화 + 브라우저 TTS). 본 앱과 무관, `/listening-pingpong.html`로 서빙. 실제 학습 흐름(**어휘 → 표현 → 리스닝**)을 재현: 예시마다 어휘 카드 → 그 어휘가 든 표현 문장 단어 배열 → 그 표현이 쓰인 A/B 대화 리스닝(B 턴 3개를 영어 3지선다, 첫 B 턴부터 문제). 대화는 텍스트 없이 음성만 나오고, 배운 표현·어휘가 나온 줄은 **다 들은 뒤** 말풍선을 텍스트로 열어 형광펜(표현)·점선 밑줄(어휘)로 짚어준다. 선택지는 답한 뒤 같은 방식으로 강조하며, 정답 박스는 이번에 방금 배운 표현이면 "방금 배운 표현", 예전에 배운 표현이면 "배운 표현"으로 구분한다. 다 풀면 done 화면에서 전체 스크립트를 텍스트로 확인할 수 있다. 표현은 실제 표현 뱅크(ExpressionUnitKR) 항목이고, 오답에도 배운 표현을 (틀린 맥락으로) 넣어 표현 인지만으로 정답을 유추하지 못하게 한다. 어휘는 실제 어휘 뱅크(Dictionary/DictionaryKR)의 seq·뜻을 쓰고, 발음은 뱅크 실음성(`speech.epop.ai/sentence/actor/{voice}/{dictSeq:07d}.{voiceHash}.ogg` — dictSeq는 Dictionary.seq, voiceHash는 Voice 테이블 `infos[voiceIdx].hash`; 단어 오디오도 문장과 같은 `sentence/actor` 경로를 쓴다)을 재생하고 실패 시 브라우저 TTS로 폴백한다. A/B 대화는 서로 다른 음성(여성/남성 우선)으로 재생하며 홈에서 각각 고를 수 있다.

화면 흐름: 스토리 선택 → 에피소드(토픽) 목록 → 시작 화면(모드 선택) → 세션(리딩/리스닝 재생) → 퀴즈(바텀시트). `App.tsx`가 상태기계로 관리(`mode`·`playing` 상태).

## 데이터 파이프라인

`dialogs.json`은 커밋된 생성물이자 런타임의 유일한 소스다(sqlite 없이도 앱은 동작). 재생성할 때만 `scripts/extract.py`를 쓰고, **손으로 편집하지 말 것**.

- 출처: bi의 `server.sqlite` (이 레포 밖). 경로는 `READING_POC_SQLITE` 환경변수 또는 CLI 인자로 지정. 없으면 명확한 에러로 종료한다.
  - 필수 테이블: `ConversationDialogScriptKR`(스크립트 + `voiceInfos` 해시), `ResourceFileKR`의 `ConversationCourses`(코스/토픽 + 대화별 `di[].h` = dialogHash). 사전 전용 오래된 export에는 대화 테이블이 없으니 **최신 export를 쓸 것**.
- 포함 코스: `INCLUDE = [2(뉴욕여행·추천), 25(잡스), 17(투자)]`(배열 순서 = 화면 표시 순서), 레벨 A2(=2) 고정. 첫 코스(2)는 `StoryList`에서 "추천" 배지.
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

- **노출 규칙**: 청크 i는 (i+N)번째 청크가 등장하는 순간 사라진다(항상 최근 N개 유지). 문장 끝의 마지막 N개는 등장할 다음 청크가 없으므로, 평균 dwell 간격으로 하나씩 빠지게 스케줄을 이어붙인다(그러지 않으면 마지막 창이 동시에 사라져 끝 청크를 볼 시간이 부족 — `buildRevealSchedule`의 `showAtExt`, 간격 상한 `DRAIN_STEP_MS`). dwell = `max(100ms, 음절수 × 속도설정)`(하한이 높으면 짧은 단어가 바닥에 걸려 속도 설정이 안 먹히므로 `MIN_DWELL_MS`는 낮게 유지). 기본은 opacity 페이드(등장 450ms, 사라짐은 250ms로 더 빠르게, 자리는 유지)이며 등장/사라짐을 각각 "페이드 인"(`fadeIn`)·"페이드 아웃"(`fadeOut`)으로 끌 수 있다. transition은 `DialogBubble`이 방향별로 인라인 지정한다(값이 바뀌는 순간의 transition이 등장/사라짐을 결정 — 보이면 fadeIn, 숨기면 fadeOut). "오래된 청크 숨기기"를 끄면(`hideOld=false`) 창 크기를 무시하고 문장 끝까지 누적한다. 상세는 `reveal.ts`.
- **퀴즈 정답은 반드시 노출되는 턴(현재 4턴) 안에 있어야 한다.** `MAX_SCRIPTS`를 줄이면 정답이 잘린 문제가 생기므로 해당 퀴즈를 재작성해야 한다. 재생성 후 `dialogs.json`에 정답 근거 문구가 있는지 확인할 것.
- **localStorage 키**: `reading-poc:settings`(설정) · `reading-poc:solved`(푼 토픽). 기존 저장값이 있으면 기본값보다 우선하므로, 새 기본값 확인 시 저장소를 비운다.
- **모드 선택·다시 듣기**: 토픽 진입 시 `SessionStart`(모드 선택 + 리딩 설정)를 거쳐 재생. 리딩 노출 설정은 리딩 모드에서만 노출. 퀴즈의 "다시 듣기"는 시작 화면을 건너뛰고 **같은 모드로 즉시** 처음부터 재생(`sessionRun` 증가로 세션 리마운트).
- **리스닝 재생**: 문장 단위 오디오를 순차 재생, `ended`(또는 `error`)에 다음으로. 자동재생은 시작 버튼 클릭(사용자 제스처) 직후라 허용된다. 텍스트는 숨기고 재생 중 말풍선에만 웨이브 인디케이터를 표시.
- **고정 재생**: `FixedSession`이 화면 중앙 한 곳에서 단어/청크를 제자리 교체(RSVP). 창·페이드·hideOld 등은 무관하고 **노출 단위(단어/청크)와 속도(ms/음절)만** 따른다(dwell = `max(100ms, 음절수×속도)`, `reveal.ts`의 `dwellMs` 재사용). 대화 맥락은 현재 화자(A/B)·진행바로 유지. 시작 화면에서 고정 모드는 단위·속도만 조절.
- **전광판 재생**: 시작 화면에서 하위 방식(`marqueeStyle`)을 고른다. `MarqueeSession`은 진입점으로 방식에 따라 분기.
  - **문장별**(`sentence`, 기본): 각 말풍선(`MarqueeSentenceSession`)이 자기 텍스트를 Web Animations API로 오른쪽→왼쪽 1회 흘려보낸다(`overflow:hidden` 레인, 흐름 뒤엔 빈 말풍선). 다음 말풍선은 현재 문장이 화면에 다 들어온 시점에 **겹쳐서** 등장해 풀-스톱 없이 연속 흐른다.
  - **한 줄**(`stream`, `MarqueeStreamSession`): 고정된 한 줄 레인에서 문장 전체가 오른쪽→왼쪽으로 연속으로 흐른다(여러 단어가 이어서 보임). 화자(A/B)·진행바로 맥락 유지, 문장 단위로 순차 진행.
  - 속도는 공통 `marqueeSpeed`(px/초, 40~400).
- **Vercel 배포**: 커밋 author 이메일이 GitHub 계정(namda-on)에 등록된 주소여야 배포가 식별된다. 이 레포는 `user.email = namda1571@gmail.com`으로 설정돼 있다.
- **화자 표시는 A/B**, 에피소드 제목은 "Episode N"만 — 제목·상대역이 주제를 노출해 문제가 쉬워지는 것을 막기 위함.
- **리딩 시작 준비 신호**: 곧바로 노출되면 당황스러우므로, 첫 텍스트 자리에 dot 을 `READY_MS`(0.8s) 동안 깜빡인 뒤 재생을 시작한다(`ready` 게이트).
- **리딩 옵션 프리셋**: `SettingsPanel`은 프리셋 3개(단어 / 청크 / 누적)를 원클릭 제공하고, "직접 설정"을 펼치면 개별 옵션을 조절한다(옵션 설명은 그 안 맨 아래에 표시). 프리셋은 노출 관련 필드(단위·창·속도·hideOld·최대청크)와 **페이드 인/아웃**을 지정한다(청크 프리셋은 창2 — 다음 청크 등장 시 이전 청크가 밀려나는 슬라이딩이 보이도록, 청크·누적은 페이드 인 켜기가 기본). **끝 사라짐 간격·전광판 속도는 프리셋과 독립**(프리셋 클릭 시 유지, `matchesPreset` 판정에서도 제외). 현재 설정이 프리셋과 일치하면 하이라이트, 아니면 "커스텀" 배지.
- **설정 지속**: 설정은 `reading-poc:settings`에 저장돼 마지막 상태가 유지된다(진입 시 리셋하지 않음). 마지막에 고른 모드(`reading-poc:mode`)와 문제 유형(`reading-poc:quizType`)도 저장돼 다음 토픽 진입 시 기본 선택된다(`App`이 저장, `SessionStart`의 `initialMode`·`initialQuizType`). 기본값(`DEFAULT_SETTINGS`)은 단어·창4·속도300·hideOld켜기·**페이드 인 끄기/아웃 켜기**.
- **문제 유형**: 세션 후 문제를 시작 화면에서 고른다 — `comprehension`(객관식 이해, `quizzes.json`), `arrange`(한국어 뜻→영어 단어 순서 맞추기), `dictation`(오디오 듣고 타이핑, 대소문자·문장부호 무시 채점). 배열·받아쓰기는 `pickKeySentence`로 고른 **단일** 핵심 문장(퀴즈 정답 근거 문장)을 대상으로 하며 기존 데이터(english·translated·audioUrl)만 사용. 마지막 유형은 `reading-poc:quizType`에 저장. 다시 풀 때 유형을 바꿔 지루함을 줄인다.
- **문제 미리보기**: 이해(`comprehension`) 유형일 때만 세션 상단에 `QuestionBanner`로 질문을 처음부터 노출한다(`App`이 `showQuestion`으로 전달; 배열·받아쓰기는 어떤 문장이 나올지가 문제라 숨김). 질문은 `quizzes.json`에서 `topicSeq`로 읽고, 선택지는 끝난 뒤 `QuizSheet`에서.
- **퀴즈 보기 셔플**: 저작 데이터(`quizzes.json`)가 정답을 대부분 1번(`answerIndex:0`)에 두어 위치로 답을 유추할 수 있으므로, `Quiz`가 마운트 시 보기를 1회 셔플한다(정답 위치 균등 분산). 데이터의 `answerIndex`는 그대로 두고 런타임에서만 섞는다.
