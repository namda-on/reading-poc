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
- `scripts/build_vocab_expression.py` — **어휘→표현** 프로토타입 데이터 생성(레포 밖 CSV/xlsx → `public/vocab-expression.data.json`). 소스 경로는 `VE_EXPR_CSV`/`VE_GRAM_CSV`/`VE_VOCAB_CSV`/`VE_GSE_XLSX` 환경변수(기본 `~/Downloads`). 조인: 표현/문법 CSV의 `content_word`(트리거 어휘)+`sentence`(배열 문장)를 **어휘 CSV(`All_*.csv`)**에 `dictSeq==seq`로 조인해 어휘 학습 데이터(`learnSentence` 영어 예문의 `[단어]`=빈칸 정답, `learnSentenceMeaning` 한국어 번역의 `[뜻]`=초록 하이라이트, `meaning`, `pos`)를 붙이고, gse xlsx에서 CEFR만 보강. **문항마다 어휘와 표현/문법이 모두 달라야 하므로 패턴(표현 제목 / 문법 큰제목::소제목)당 1문항만** 뽑아 레벨 오름차순 **단일 시퀀스**로 만든다(레벨별로 묶으면 같은 패턴이 연속돼 키워드만 바뀌는 반복이 됨). 어휘도 중복 제거. 모드별 문항 수는 `VE_MAX_ITEMS`(기본 60, 0이면 전체 — 확보 가능한 패턴은 표현 267·문법 294개). 어휘 CSV의 `filter`가 `sexual`/`unnecessary`인 행은 제외. 표현 제목(`title_en`/`title_kr`, `~` 슬롯 패턴)·문법 소제목(`sub`)은 병합셀이라 **forward-fill**하고(문법은 큰제목 바뀌면 소제목 리셋). 같은 패턴의 다른 예문을 `siblings`(2개, `{word,en,kr}`)로 붙이고, 표현은 `sentence`의 `[...]`(핵심 표현 구간)·번역의 `[...]`를 `coreEn`/`coreKr`로 뽑는다(정답 후 하이라이트용, 표현 4159행 전부 마크업 있음 / 문법엔 없음). **핵심 표현 앞에 도입부(`Excuse me?`·`Yeah,` 등, `lead_in`)가 붙은 문장은 제외**해 배열 문장이 표현 자체로 시작하게 하고, **응용 예문 2개가 확보되는 패턴만**(도입부 없는 예문 3개 이상) 쓴다 — 조건 통과 패턴 164개 중 60문항 사용. **활용 규모 수치는 쓰지 않는다** — 실제 용례는 데이터보다 많을 수 있어 의미가 없다.
- `public/vocab-expression.html` — **별도** 어휘→표현 프로토타입(자체 완결형 HTML, 본 앱과 무관, `/vocab-expression.html`로 서빙). **앱(말해보카)의 어휘/문법 학습 UI·UX를 화면 그대로 재현**(참고 영상 기반). 흐름은 아이템마다 **[1] 어휘 빈칸 채우기 → [2] 문장 배열**. 상단바는 트로피·진행바(별 마커·`i/N`)·설정. 홈은 **표현/문법 탭**(마지막 탭 `ve:mode`) + **진입점 하나**(레벨 카드 없음) — 들어가면 문항마다 트리거 어휘와 표현/문법이 계속 달라진다. 홈 배치는 `탭 → 시작 카드(흐름·남은 문항 + 큰 CTA `.start-btn`) → 실험 옵션`. 진입 버튼이 다른 카드들과 같은 톤이면 눌러야 들어간다는 게 안 읽히므로 **CTA만 채운 색 버튼**으로 두고 옵션은 `실험 옵션` 헤더 아래 보조 영역에 둔다. 진행 위치는 모드별로 `ve:pos`에 저장해 `이어서 풀기`/`처음부터 다시 풀기`를 제공하고, 레벨은 문항 카드 좌상단 태그(`레벨 N`)로만 표시한다. [1] 어휘는 **채팅 말풍선 카드**(좌상단 `레벨 N` 태그·우상단 `New` 배지·상단 파란→흰 그라데이션): 한국어 번역(정답 뜻 영역 초록 `.tgt`, 괄호 설명줄 muted) 위, 영어 예문의 `[단어]`를 **인라인 입력 빈칸**(`<input class=blank>`, `field-sizing:content`로 자동 폭)으로 보여준다. 하단은 `? 힌트 보기` / `🎤 음성 모드`(비작동). 힌트는 **순차** — `? 힌트 보기`(**앞 2글자**+나머지 길이) → `✔ 정답 보기`(정답 전체, `.blank.revealed`). 둘 다 **placeholder로** 보여주므로 입력값이 남아 있으면 가려져 아무 반응이 없는 것처럼 보인다. 그래서 **정답 보기를 누를 때만 입력값과 오답 박스를 지워** 정답 placeholder가 보이게 하고(힌트 보기는 입력값을 유지), 그 뒤 다시 타이핑해도 정답이 가려지지 않게 **문장 아래에 `정답 {단어}` 주석 한 줄**(`#revealNote`)을 남긴다(정답을 맞히면 숨김). **정답 입력 시 확인 없이 즉시 처리**(`norm`), 오답은 **카드 안 파란 박스**에 `{입력} - 정답과 N글자 달라요`로 틀린 글자 빨강(`diffSpell`). 정답이면 **카드가 초록으로 바뀌고 ✓ 체크** → 정답 단어 초록 박스 + 하단이 **탭(다른 예문·오답 노트·AI 질문 답변·사전 검색·단어 정보) + 3버튼(단어 듣기·다시 듣기·다음 문제)**로 교체(다음 문제만 작동). 빈칸 정답은 표제어와 같아야 하므로 굴절형·부분구 예문(be→[am] 등)은 빌드 제외. [2] 배열은 **말풍선 카드**(한국어 A 대사) + **인라인 문장 채우기**(빈 밑줄에 뱅크 단어를 순서대로 탭해 채움, 종결부호 고정) + **단어 뱅크(자리 유지 — 채운 타일은 회색 빈칸으로 남김)** + `정답 보기`/`확인`. 타일은 소문자(첫 단어 노출 방지). 방해 단어는 현재 없음(데이터 준비되면 추가).
  **어휘→표현 연결은 텍스트 설명이 아니라 행위로 체감시킨다**(긴 안내 문구는 한 번에 안 읽히고, 트리거 어휘가 표현의 핵심이 아닐 때 어색해짐):
  - 연결 강화 장치 3종은 **개별 on/off 옵션**(`ve:opts` = `{banner,preview,fly}`, 기본 `preview`만 ON)으로 조합을 비교할 수 있다. 홈 옵션 박스와 세션 중 상단 기어 팝오버 양쪽에서 토글한다.
    - `banner` — 상단바 아래 **단계 배너**(`#stepBanner`, 화면 전환과 무관하게 유지되는 노드): `① 어휘 익히기 → ② 표현 만들기`. 어휘를 맞히면 1단계가 `✓ {단어}` 초록 칩으로 바뀌어 **표현 화면까지 그 단어를 데려간다**. 두 화면이 한 문항의 1·2단계임을 알리는 동시에 단어 캐리오버를 담당(문법은 `② 문장 만들기`). 상태 클래스는 `.sb-step.solved` — 완료 화면의 `.done`(`flex:1; flex-direction:column`)과 겹치면 배너가 깨지므로 `done`을 쓰지 않는다. 옵션 스위치는 `.opt-sw`다 — `.sw`는 응용 예문에서 **바뀐 단어 강조**에 이미 쓰이므로, 스위치에 `.sw`를 쓰면 노브(`::after`의 흰 원)가 예문 글자 위에 그려진다. **짧고 일반적인 클래스명을 새로 만들 때 기존 정의와 겹치는지 먼저 확인할 것**(`.done`·`.sw` 둘 다 이 방식으로 깨졌다).
    - `preview` — 어휘 정답 직후 **다음 단계 예고**: `다음 문제` 버튼 위에 그 버튼을 가리키는 **말풍선**(`.tip-bubble`, `이제 이 단어를 써볼까요?`)을 띄운다. 버튼 문구는 그대로 둔다(단어를 넣어 `{단어} 써보기`로 바꾸면 어색함). 말풍선이 위 탭 라벨을 가리지 않도록 `.vbtns.has-tip`으로 버튼 줄을 내린다.
    - `fly` — 초록 정답 칸에서 다음 화면의 그 단어 자리(배너 칩, 없으면 트리거 타일)로 **단어가 날아가 앉는 이동 연출**(`flyWord`, FLIP 방식 0.5s).
  - 이 장치들이 필요한 이유: 어휘 예문(`Do you have a pen?`)과 표현 문장(`Can I have a pen?`)은 **서로 다른 문장**이고 공유하는 건 단어 하나뿐이라, 화면을 그냥 교체하면 별개 문제 두 개로 읽힌다.
  - 배열 전 보라 박스(`learnBoxHtml`)는 **뭘 배우는지만** 짧게 보여준다 — `이번에 배울 표현/문법` 라벨 + **패턴 한국어 뜻**(`pattern_kr`) 두 줄. 상황 태그(일상/여행/비즈니스)와 활용 규모 수치(`N가지`)는 **쓰지 않는다** — 태그는 콘텐츠에서 없어질 수 있고, 수치는 실제 용례가 더 많을 수 있어 의미가 없다. **영어 프레임(`pattern_en`)은 정답 어순이 새므로 배열 전엔 절대 노출하지 않는다.** 어휘 연결은 문구가 아니라 칩 강조가 담당.
  - **방금 배운 어휘 칩을 초록으로 강조**(`.tile.trigger` + 배지 + 펄스). 배지 내용은 **옵션**(`ve:chipLabel`: `learned`=`방금 배운` / `meaning`=그 어휘의 뜻, 기본 `meaning`)으로 고르며, 홈의 세그먼트 컨트롤과 세션 중 상단 기어(설정 팝오버) 양쪽에서 바꿀 수 있고 세션 중 전환 시 즉시 반영된다(`applyChipLabels`, CSS `content:attr(data-label)`). 뜻 라벨은 `shortMeaning`이 `<주석>`·`(부연)`을 떼고 앞쪽 뜻만 10자 내로 줄인다. 어휘 단계의 초록 정답과 색을 이어 "그 단어"임을 인지시킨다. 어느 타일이 그 어휘인지는 `isTriggerToken`이 판정 — 정확일치 + 규칙 굴절형(days/going/taxes/fatter/dancing/parties, 소유격 `toilet's`, 복합어 `Round-trip⊃trip`)까지 인정하고 **하이픈 조각 단위로 비교**해 `wondering⊃ring` 같은 오탐을 막는다. 매칭률은 표현 100% · 문법 대부분이고, `spoke`·`best`·`said`·`gone` 같은 불규칙만 미매칭 → 강조·연출을 생략하는 폴백으로 동작한다.
  - 그 칩을 문장에 넣는 순간 **'써먹었다' 연출**(`fireUsedEffect`): 팝 + 링 반사 + `방금 배운 단어!` 배지 + 햅틱(`navigator.vibrate`, Android만). 문항당 1회만 발동(반복 피로 방지).
  - 정답 시 **초록 카드 + ✓ + 완성 문장** 아래에 **보상 카드**(`patternPayoffHtml`)를 붙인다. 완성 문장과 응용 예문은 모두 `hlExpr`로 렌더한다 — **핵심 표현 구간(`coreEn`)은 형광펜(`.core`), 그 뒤 단어가 바뀌는 영역은 밑줄(`.rest`), 그 안의 해당 어휘는 초록(`.tgt`/`.sw`)**. 표현 60/60 적용, 문법은 core 마크업이 없어 어휘만 강조하는 폴백(문장 전체가 곧 문법 패턴이라 구간 구분이 불필요). 보상 카드는 `🎉 새로운 표현/문법을 배웠어요` + **재사용 프레임 공개**(표현은 `pattern_en`의 `~`를 빈칸으로 그린 틀 + 한국어 뜻, 문법은 문법 포인트) + `단어만 바꿔서 이렇게도 말할 수 있어요` + **응용 예문 2개**(`siblings`의 `en`/`kr`/`coreEn`). 배열 중엔 숨겨둔 영어 틀을 정답 후에 처음 공개하는 구성이라 보상에 새 정보가 담긴다(단순 재진술이면 효용이 안 느껴짐). 데이터 스키마: `modes.{expression,grammar}.items[]` = `{level,word,meaning,pos,cefr,vocab{answer,enLines,koLines},sentence{en,kr,trigger,pattern_en?,pattern_kr,coreEn?,coreKr?,siblings}}`. TTS·음성 등 앱 부가기능은 시각적으로만 재현(비작동), 리딩·타이핑 중심.
- `public/listening-pingpong.html` — **별도** 리스닝 핑퐁 프로토타입(자체 완결형 HTML + 브라우저 TTS, 본 앱과 무관, `/listening-pingpong.html`로 서빙). 콘텐츠는 외부 JSON에서 로드: `listening-pingpong.data.json`(초급 A1-A2) + `listening-pingpong.data.b.json`(중급 B1-B2). 홈은 **초급/중급 그룹**으로 나눠 보여주고, 완료한 대화는 `localStorage`(`lp:cleared`)에 저장해 ✓ 완료 배지·`n/N 완료` 카운트로 표시(하나씩 클리어). 흐름은 **표현(단어 배열) → 리스닝**: A(상대)가 트리거 문장을 말하고 B(학습자)가 3지선다로 답하는 오청(mishearing) 함정 퀴즈. A 대사는 텍스트 없이 음성만(시작 전 3·2·1 카운트다운), 답하면 각 선택지의 한국어 뜻·해설을 보여준다. **답한 뒤**에는 그 A 말풍선을 탭해 영어 대사를 펼쳐 볼 수 있다(답하기 전엔 잠금 — 훈련 훼손 방지, `setupPeek`/`unlockA`). 홈의 **'A 노출' 옵션**(`lp:expose`)으로 A 대사 방식을 고른다: `듣기`(음성) 또는 `고정·읽기`(음성 없이 단어를 하나씩 제자리 교체하는 RSVP, `rsvpReveal`) — 리딩은 **대화 영역(chat) 위에만 겹치는 중앙 오버레이**로, 뒤 대화를 흐리게(blur) 덮고 상단 진행바는 유지하며 부드럽게 페이드 인/아웃한다(화면 통째 교체 금지 — 되돌아올 때 끊김 방지, `chat.getBoundingClientRect()`로 위치·크기 지정). 고정 모드에선 **속도 설정이 RSVP 속도를 겸하고**(음절수×280/rate), 준비 문구·다시 보기가 모두 '보기'로 바뀐다. **틀리면** A 대사를 다시 접하고 그 문장을 단어 배열로 재구성하는 교정 단계가 뜬다(`buildArrange`) — 듣기는 오답 뒤 음성을 자동 재생하지만, **고정은 갑자기 뜨지 않도록 '👀 다시 보기'를 눌러야** 리딩이 노출된다(`makeRsvpPlayer`, 자동 재생 없음). 표현이 나온 트리거 문제에서는 정답 후 "🎧 방금 A가 이렇게 말했어요 + 그 문장 + 배운 표현" 박스로 연결해준다. done 화면에서 전체 스크립트(영어+한국어)를 볼 수 있다. 데이터 스키마: `examples[]`에 `vocab`·`expression{csv_id,en,kr}`·`dialogue[{role,text,kr}|{role:'B',choices:[{text,kr,correct,trap,explain,highlight}]}]`; 표현은 실제 표현 뱅크(ExpressionUnitKR) 항목(csv_id=seq), '표현 배열' 문장은 트리거 A 대사(표현에 `~`가 있으면)에서 자동 생성. 강조(형광펜/밑줄)는 현재 쓰지 않음. A/B는 서로 다른 음성(여성/남성 우선)으로 재생하며 홈에서 각각 고른다.
- `public/listening-pingpong-v2.html` — 리스닝 핑퐁 **UI v2**(`/listening-pingpong-v2.html`). 데이터 JSON과 `lp:*` localStorage는 v1과 공유하되 UI를 재구성: **표현(단어 배열) 선행 단계 제거**(홈 → 바로 리스닝), 화면은 **상단 문제 카드(레벨 헤더 + 대화) + 하단 답안 영역** 2단. 문제 전환은 **스왑 체인(크기 2)** — 결과를 보여주는 동안 `back` 버퍼(`visibility:hidden`이라 레이아웃·스크롤 유지)에 다음 문제 화면을 미리 렌더해 두고 '다음'에서 교체(`swapScreens`, 슬라이드 인). 각 문제 화면은 매번 새로 만드는 별개 컴포넌트고, 이전 대화 내역은 DOM 복제가 아니라 **turns 데이터에서 재렌더**(`newChatScreen`) — 위로 스크롤해 열람하되 손을 떼면 현재 문답으로 복귀(sticky, `attachSnapBack`). 답변 흐름: 답하면 B 정답 대사가 바로 말풍선으로 보이고 💡 해설(정답 초록/오답 노랑, 오답이면 고른 문장 + 수평선)이 카드에 남는다. **정답 → A 말풍선 탭 열람 허용 후 다음 문답 / 오답 → A 대사 계속 숨긴 채 문장 배열 교정 문제**(카드에 뜻·플레이어·배열 줄, 답안 영역에 단어 뱅크). 결과 영역의 **오답 노트** 버튼은 모범답안 + 오답 이유 팝업(`showWrongNote`). A 말풍선은 재생 전/후에도 정적 웨이브 유지(크기 고정).
- `public/listening-pingpong-v3.html` — 리스닝 핑퐁 **UI v3**(`/listening-pingpong-v3.html`). 데이터 JSON·`lp:*` localStorage는 v1/v2와 공유. v2의 문제 카드 안에서 **대화가 v1처럼 메신저식으로 아래로 누적**된다(스왑 체인·재렌더 없음). 채팅은 `column-reverse` 스크롤러라 하단 고정이 네이티브(scrollTop 0 = 맨 아래) — 그래서 **선택지 패널이 카드 하단에서 키보드처럼 올라올 때 대화가 위로 밀리고, 내려갈 때 함께 내려온다**(패널은 `grid-template-rows 0fr→1fr` 애니메이션, `raisePanel`/`lowerPanel`). 답하면 각 선택지에 뜻·해설이 **인라인** 표시(v1 방식, 별도 오답 노트 팝업 없음)되고 B 정답 말풍선이 채팅에 쌓이며, **'다음'을 눌러야 패널이 내려간다**. **오답 교정(문장 배열)은 화면 교체 대신 바텀 시트**(`fixSheet` — 카드 톤의 안내·뜻·플레이어·배열 줄 + 아래 단어 뱅크)가 올라와 풀고 나면 내려간다(뒤의 대화 유지). A 말풍선 열람은 정답 시 즉시, 오답 시 배열 완료 후 허용. **다시 듣기는 A 말풍선 안 스피커 버튼**(구분선 옆 본문은 웨이브 → '영어 보기' → 영어 전문으로 바뀜, 각 말풍선이 자기 대사를 재생) — 카드 하단 버튼 없음.

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
