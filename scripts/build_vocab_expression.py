#!/usr/bin/env python3
"""어휘→표현 프로토타입 데이터 생성 (버전 A/B 공용).

소스(레포 밖, 기본값은 ~/Downloads):
  - 표현 CSV: `유기적 통합모드 문장 (공유용)` — 그룹(id)당 트리거 어휘 + 표현 패턴 +
    문장 3~6개(문장1 = 트리거가 들어간 대표 문장) + 결과 카드(형태/뜻/설명)
  - 어휘 CSV(All_*.csv): seq(=dictSeq) → learnSentence(영어 예문, [단어]=빈칸 정답)
    + learnSentenceMeaning(한국어 번역, [뜻]=초록) + meaning + pos
  - gse CSV: dictSeq → 어휘 레벨(1~30) + CEFR

두 버전이 같은 문항을 써야 비교가 되므로 **양쪽 모두 성립하는 그룹만** 남긴다.
  - 버전 A: 어휘 학습 문장 = 어휘 CSV의 learnSentence (표현 문장과 다른 문장)
  - 버전 B: 어휘 학습 문장 = 표현 문장(문장1)에서 트리거 어휘를 빈칸으로

[3] 슬롯 치환 단계(`apply`)도 함께 굽는다. 목적은 **유저가 프레임을 직접 산출**하는 것이라
슬롯(변하는 부분)은 주어진 채로 고정하고 프레임 자리를 비운다.

프레임은 `form`(J열) 표기가 아니라 **학습 문장(D열)에서 직접 추출**한다 — `form`에는
`주어 + didn't + ______`처럼 한글 자리표시자나 `What / Who / Where`처럼 대안이 박힌
표기가 많아 문장에 그대로 등장하지 않는다. 문장1과 다른 문장의 **공통 연속 구간**을
difflib으로 뽑아 프레임 후보로 쓰고, 문장1을 포함해 가장 많은 문장을 커버하는 후보를
고른다. 1단어 조각 두 개로 된 프레임은 실제 패턴을 잃으므로(`Can/Could you ~?` →
`you`+`me`) **단일 연속 구간 2단어 이상**만 인정한다.

출력: public/vocab-expression.data.json (커밋되는 생성물). 손으로 편집하지 말 것.
"""
import csv, json, os, re, sys
from difflib import SequenceMatcher
from collections import OrderedDict
from pathlib import Path

DL = Path.home() / "Downloads"
EXPR_CSV  = Path(os.environ.get("VE_EXPR_CSV",  DL / "유기적 통합모드 문장 (공유용) - 문장 제출(0827).csv"))
VOCAB_CSV = Path(os.environ.get("VE_VOCAB_CSV", DL / "All_(2026-09-01_20_14_12).csv"))
GSE_CSV   = Path(os.environ.get("VE_GSE_CSV",   DL / "gse_corrected_final_0624 - 보정결과_전체.csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "vocab-expression.data.json"
# [5] 상황 단계용 A 대사 — 소스 CSV에 상황 필드가 없어 손으로 적은 프로토타입 문안
SITUATIONS = Path(__file__).resolve().parent / "vocab_expression_situations.json"

MAX_ITEMS = int(os.environ.get("VE_MAX_ITEMS", "0"))    # 0이면 전체
VOCAB_FILTER_SKIP = {"sexual", "unnecessary"}
BRACKET = re.compile(r"\[([^\]]+)\]")
INFL = re.compile(r"^(?:s|es|ed|d|ing|er|est|ies|ier|iest|'s|')$")
WORD = re.compile(r"[A-Za-z']+")
SLOT_MARK = re.compile(r"_{2,}|~")
KOR = re.compile(r"[가-힣]")
# 홑 대명사 조각은 표현의 일부가 아니라 그 자리에 오는 주어·목적어다.
# `get up`을 배우는데 `You` … `get up`이 프레임으로 잡히면 안 된다.
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they",
            "me", "him", "her", "us", "them"}
MIN_FRAME_WORDS = int(os.environ.get("VE_MIN_FRAME_WORDS", "2"))


def die(msg):
    print(f"[build_vocab_expression] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def strip_markup(s):
    return (s or "").replace("[", "").replace("]", "").replace("{", "").replace("}", "").strip()


def clean_meaning(m):
    """뜻 정리. 실제 뜻은 `ⓜ` 줄에 있고 첫 줄은 `( Phrasal Verb )` 같은 머리글일 수 있으므로
    ⓜ 줄을 우선 쓰고, 없으면 머리글·용법(ⓤ) 줄을 건너뛴 첫 줄을 쓴다."""
    lines = [x.strip() for x in (m or "").split("\n") if x.strip()]
    pick = ""
    for ln in lines:
        if ln.startswith("ⓜ"):
            pick = ln
            break
    if not pick:
        for ln in lines:
            if ln.startswith("ⓤ") or re.fullmatch(r"\(.*\)", ln):
                continue
            pick = ln
            break
    return re.sub(r"^[^\w가-힣<(]+", "", (pick or (lines[0] if lines else "")).strip()).strip()


def short_meaning(m, limit=14):
    """빈칸 힌트용 짧은 뜻: <주석>·(부연) 제거 후 앞쪽 뜻만."""
    t = re.sub(r"<[^>]*>", " ", m or "")
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    out = ""
    for p in [x.strip() for x in re.split(r"[,;/]", t) if x.strip()]:
        cand = f"{out}, {p}" if out else p
        if len(cand) > limit:
            break
        out = cand
    return out or t[:limit]


# 용언 어미 — 뜻(`공부하다`)과 문장(`공부 안 했어`)을 잇기 위해 어간만 남긴다
KR_SUFFIX = ("하다", "되다", "이다", "시키다", "스럽다", "롭다", "다", "은", "는", "한", "인", "적인", "적")


def kr_meaning_spans(meaning):
    """뜻에서 한국어 문장과 맞춰볼 후보들(긴 것부터)."""
    t = re.sub(r"<[^>]*>", " ", meaning or "")
    t = re.sub(r"\([^)]*\)", " ", t)
    out = set()
    for part in re.split(r"[,;/]", t):
        part = part.strip()
        if not part:
            continue
        out.add(part)
        for suf in KR_SUFFIX:
            if part.endswith(suf) and len(part) > len(suf):
                out.add(part[: -len(suf)])
    return sorted({x for x in out if x}, key=len, reverse=True)


def mark_meaning_kr(kr, meaning, authored=""):
    """한국어 문장에서 어휘 뜻에 해당하는 구간을 [..]로 감싼다. 못 찾으면 None.

    앱의 어휘 학습은 번역문에서 정답 어휘의 뜻만 초록으로 보여준다. 표현 문장에는
    그 마크업이 없으므로 뜻 조각(어간 포함)을 문장에서 직접 찾는다.

    `authored`는 어휘 CSV 예문 번역에 **저작된** `[뜻]`이다. 사전 뜻보다 문맥에 맞는
    구어체라 먼저 시도한다(`should`의 사전 뜻 `해야 한다`는 `일어나야 해.`에 없지만
    저작된 `야 해`는 있다). 그래도 못 찾는 경우가 남으므로 그때는 별도 힌트 줄로 대체한다.
    """
    cands = []
    for a in sorted(re.findall(r"\[([^\]]+)\]", authored or ""), key=len, reverse=True):
        cands += kr_meaning_spans(a)
    cands += kr_meaning_spans(meaning)
    for cand in cands:
        if len(cand) >= 2:
            i = kr.find(cand)
            if i >= 0:
                return kr[:i] + "[" + cand + "]" + kr[i + len(cand):]
        else:
            # 한 글자 뜻은 낱말 첫머리에서만 인정 (우연 일치 방지)
            mm = re.search(r"(?:^|\s)(" + re.escape(cand) + r")", kr)
            if mm:
                i = mm.start(1)
                return kr[:i] + "[" + cand + "]" + kr[i + len(cand):]
    return None


def infl_match(tok, base):
    """tok이 base와 같거나 규칙 굴절형인지 (parents←parent, teaches←teach)."""
    t, b = tok.lower(), base.lower()
    if not t or not b:
        return False
    if t == b:
        return True
    if t.startswith(b):
        rest = t[len(b):]
        if len(rest) > 2 and rest[0] == b[-1]:      # CVC 자음 중복 (fatter)
            rest = rest[1:]
        if not rest or INFL.match(rest):
            return True
    stem = re.sub(r"[ey]$", "", b)                  # dance→dancing, party→parties
    return len(stem) >= 3 and stem != b and t.startswith(stem) and bool(INFL.match(t[len(stem):]))


def blank_trigger(sent, trigger):
    """문장에서 트리거 어휘 한 곳을 [..]로 감싼다. 못 찾으면 None.

    여러 단어 트리거(`ice cream`)는 구 전체를 찾는다 — 토큰 하나씩 비교하면
    문장에 그대로 있어도 매칭되지 않는다. 단일 단어는 정확일치 우선, 없으면 규칙 굴절형.
    """
    ws = str(trigger).split()
    if len(ws) > 1:
        # 마지막 단어의 규칙 복수/3인칭만 허용 (video game → video games)
        pat = r"\b" + r"\s+".join(re.escape(w) for w in ws[:-1]) + r"\s+" + re.escape(ws[-1]) + r"(?:s|es)?\b"
        mm = re.search(pat, sent, re.I)
        if mm:
            return sent[: mm.start()] + "[" + mm.group(0) + "]" + sent[mm.end() :], mm.group(0)
        return None

    best = None
    # 앞따옴표를 토큰에 포함시키지 않는다 ('inappropriate' 같은 인용 표기)
    for m in re.finditer(r"[A-Za-z]+(?:'[A-Za-z]+)*", sent):
        if m.group(0).lower() == trigger.lower():
            best = m
            break
        if best is None and infl_match(m.group(0), trigger):
            best = m
    if not best:
        return None
    return sent[: best.start()] + "[" + best.group(0) + "]" + sent[best.end() :], best.group(0)


def lexical_form(form):
    """`form`이 **어휘 표현**인가 — 한글 자리표시자(`주어`,`명사`)나 대안(`Do / Does`)이 섞이면
    문법 틀이다. 문법 틀은 문장마다 표현 자체가 변형되므로([3]에서 `Don't you drive?`와
    `Don't they work with you?`가 같은 프레임으로 잡힌다) 경계가 정해지지 않는다.
    [3]은 **한 청크를 그대로 다시 쓰는** 과제라 어휘 표현만 확실하다."""
    f = (form or "").strip()
    return bool(f) and not KOR.search(f) and "/" not in f


def words(sent):
    return WORD.findall(re.sub(r"[.?!]+$", "", sent.strip()))


def form_words(form):
    """`form`의 어휘 내용을 (필수, 선택) 두 묶음으로 나눈다.

    괄호 안은 저작자가 **선택**으로 표시한 것이다 — `come over (to ______)`의 `to`는
    없어도 같은 표현이다. `(= turn ______ off)` 같은 부기도 괄호 안이라 선택으로 본다.
    """
    f = form or ""
    optional = set()
    for inner in re.findall(r"\(([^)]*)\)", f):
        optional |= {w.lower() for w in WORD.findall(inner)}
    required = {w.lower() for w in WORD.findall(re.sub(r"\([^)]*\)", " ", f))}
    return required, optional | required


def form_pieces(form):
    """`form`의 리터럴 조각들을 순서대로 반환(괄호 안은 선택 취급해 제거).

    `put ______ on` → ['put', 'on'] · `the ______ of the ______` → ['the', 'of the'] ·
    `get up` → ['get up'] · `come over (to ______)` → ['come over'].
    """
    f = re.sub(r"\([^)]*\)", " ", form or "")
    out = []
    for part in SLOT_MARK.split(f):
        ws = WORD.findall(part)
        if ws:
            out.append(ws)
    return out


def frame_matches_form(frame, form):
    """프레임이 `form`의 어휘 내용과 **구조까지** 같은가(굴절 허용).

    조각 개수와 순서가 맞아야 한다 — `the ______ of the ______`는 조각이 둘(`the`,`of the`)인데
    프레임이 `of the` 하나로 잡히면 표현의 일부만 떼어낸 것이고, `What does ______ do ?`도
    끝의 `do`가 빠지면 표현이 아니다. 괄호 안 낱말은 있어도 없어도 되는 것으로 본다
    (`all (of) ______`의 `of`).
    """
    pieces = form_pieces(form)
    if not pieces or len(pieces) != len(frame):
        return False
    _, optional = form_words(form)

    def same(a, b):
        return a == b or infl_match(a, b) or infl_match(b, a)

    for want, got in zip(pieces, frame):
        want_l = [w.lower() for w in want]
        got_l = [w.lower() for w in got.split()]
        for g in got_l:
            if not any(same(g, w) for w in want_l) and g not in optional:
                return False
        for w in want_l:
            if not any(same(g, w) for g in got_l):
                return False
    return True


# 흩어진 기능어 조각들은 실제 패턴이 아니다 — `Can/Could you ~?`에서 `you` … `me`가
# 뽑히면 정작 `Can/Could`가 빠진다. 반면 **붙어 있는 한 덩어리**는 기능어만이어도
# 정상 패턴이다(`How about`, `What if`)므로 이 검사는 두 조각 이상에만 쓴다.
FUNCTION_WORDS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "mine", "yours",
    "this", "that", "these", "those", "there", "here",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "will", "would", "can", "could", "shall", "should", "may", "might", "must",
    "a", "an", "the", "and", "or", "but", "if", "so", "not", "no", "than", "as",
    "what", "who", "whom", "whose", "where", "when", "why", "how", "which",
    "to", "of", "in", "on", "at", "for", "with", "from", "by", "about", "too", "very",
}

# 한정사·소유격은 뒤따르는 슬롯(명사구)에 속하므로 프레임 끝에 남기지 않는다.
DETERMINERS = {"a", "an", "the", "my", "your", "his", "her", "its", "our", "their",
               "this", "that", "these", "those", "some", "any"}


def has_content(lits):
    return any(w.lower().strip("'") not in FUNCTION_WORDS
               for lit in lits for w in lit.split())


def trim_determiners(lits):
    """조각 끝의 한정사를 떼고, 한정사만으로 된 조각은 버린다.

    `Put your` … `on` → `Put` … `on` (슬롯 `your coat`).
    다듬은 결과가 프레임으로 성립하지 않으면 원본을 그대로 돌려준다(`It's a` 등).
    """
    out = []
    for lit in lits:
        ws = lit.split()
        while ws and ws[-1].lower() in DETERMINERS:
            ws.pop()
        if ws:
            out.append(" ".join(ws))
    if out and sum(len(x.split()) for x in out) >= MIN_FRAME_WORDS:
        return out
    if len(lits) == 1:
        return lits      # `It's a` — 한 덩어리는 한정사로 끝나도 프레임이 된다
    return None          # 조각이 한정사뿐이면 프레임 조각이 아니다


def frame_candidates(base, other):
    """두 문장의 공통 구간에서 프레임 후보를 만든다(원문 대소문자 유지).

    한 덩어리(`talk to`)뿐 아니라 **떨어진 두 덩어리**(`put` … `on`)도 후보로 낸다 —
    분리형 구동사는 슬롯이 프레임 사이에 들어가므로 연속 구간만 보면 particle(`on`)이
    슬롯으로 새어 들어간다(`put your` + 슬롯 `coat on`).
    """
    wb, wo = words(base), words(other)
    lb, lo = [w.lower() for w in wb], [w.lower() for w in wo]
    blocks = [x for x in SequenceMatcher(None, lb, lo, autojunk=False).get_matching_blocks() if x.size]
    lits = [(x, " ".join(wb[x.a : x.a + x.size])) for x in blocks]

    out, seen = [], set()

    def add(cand):
        cand = trim_determiners(cand)
        if cand is None or sum(len(x.split()) for x in cand) < MIN_FRAME_WORDS:
            return
        if len(cand) > 1 and not has_content(cand):
            return
        if any(x.lower() in PRONOUNS for x in cand):
            return      # 홑 대명사 조각 — 표현이 아니라 그 자리에 오는 주어·목적어
        key = tuple(x.lower() for x in cand)
        if key in seen:
            return
        seen.add(key)
        out.append(cand)

    for _, lit in lits:
        add([lit])
    for i in range(len(lits)):
        for j in range(i + 1, len(lits)):
            add([lits[i][1], lits[j][1]])
    return out


# [3] 함정 단어 — 같은 자리에 올 수 있는 **같은 부류**의 낱말이어야 고민이 생긴다.
# 엉뚱한 품사를 섞으면 오히려 정답이 더 뻔해진다. 순서대로 검사하므로 particle을 prep보다 앞에 둔다.
TRAP_BUCKETS = [
    ("particle", ["on", "off", "up", "down", "out", "over", "back", "away", "through", "along"]),
    ("prep", ["to", "for", "with", "about", "from", "at", "of", "by", "into", "in"]),
    ("auxneg", ["don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
                "won't", "can't", "couldn't", "shouldn't", "haven't", "hasn't"]),
    ("aux", ["do", "does", "did", "is", "are", "was", "were", "am",
             "will", "would", "can", "could", "should", "have", "has", "had"]),
    ("pron", ["i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"]),
]
TRAP_LIMIT = int(os.environ.get("VE_TRAPS", "2"))


# 내용어(동사·명사)는 부류 목록을 만들 수 없으므로, **다른 표현의 프레임에서 쓰인 낱말**을
# 빌려 함정으로 쓴다. 실제 표현에 등장하는 낱말이라 엉뚱하지 않고, 길이가 비슷한 것만 고른다.
CONTENT_TRAP_POOL = []


def make_traps(frame, sentence):
    """프레임의 각 기능어 자리에 같은 부류의 다른 낱말을 함정으로 하나씩 붙인다.

    내용어(동사·명사)는 대체 후보를 데이터에서 만들 수 없으므로 건너뛴다. 문장에 이미
    쓰인 낱말은 정답으로 보일 수 있어 제외한다. 난수를 쓰지 않고 문장 해시로 고르므로
    빌드가 재현된다.
    """
    used = {w.lower() for w in re.findall(r"[A-Za-z']+", sentence)}
    seed = sum(ord(c) for c in sentence)
    traps = []
    for lit in frame:
        for w in lit.split():
            wl = w.lower()
            for _, pool in TRAP_BUCKETS:
                if wl not in pool:
                    continue
                cands = [x for x in pool if x != wl and x not in used and x not in traps]
                if cands:
                    traps.append(cands[(seed + len(traps)) % len(cands)])
                break
            if len(traps) >= TRAP_LIMIT:
                return traps
    if traps:
        return traps
    # 기능어가 없는 프레임 — 다른 표현의 프레임 낱말을 길이가 비슷한 것 중에서 빌려 온다
    for lit in frame:
        for w in lit.split():
            cands = [x for x in CONTENT_TRAP_POOL
                     if abs(len(x) - len(w)) <= 2 and x != w.lower() and x not in used]
            if cands:
                traps.append(cands[(seed + len(traps)) % len(cands)])
            if len(traps) >= 1:
                return traps
    return traps


def slots_clean(lits, sents, cov):
    """커버되는 문장들의 슬롯이 공통 단어를 갖지 않는가.

    슬롯에 모든 문장이 공유하는 단어가 남아 있으면 그건 아직 프레임의 일부라는 뜻이다
    (`put your` + 슬롯 `clothes on`/`coat on` → `on`이 남아 있으므로 프레임이 미완성).
    """
    shared = None
    for i in cov:
        sd = segment(sents[i], lits)
        ws = {w.lower() for x in sd["segs"] if x["t"] == "slot" for w in x["s"].split()}
        shared = ws if shared is None else (shared & ws)
        if not shared:
            return True
    return not shared


def extract_frame(sents):
    """문장1을 반드시 포함하면서 가장 많은 문장이 공유하는 프레임을 고른다.

    반환 (리터럴 목록, 커버하는 문장 인덱스). 못 찾으면 None.
    우선순위: 커버 문장 수 → 슬롯이 깨끗한지 → 프레임 길이 → 조각 수.
    커버를 최우선에 두면 한 문장에만 맞는 과적합 프레임(`Don't be late`)을 걸러낸다.
    """
    best = None
    for j in range(1, len(sents)):
        for lits in frame_candidates(sents[0], sents[j]):
            cov = [i for i, s in enumerate(sents) if segment(s, lits) is not None]
            if not cov or cov[0] != 0 or len(cov) < 2:
                continue
            key = (len(cov), slots_clean(lits, sents, cov),
                   sum(len(x.split()) for x in lits), len(lits))
            if best is None or key > best[0]:
                best = (key, lits, cov)
    return (best[1], best[2]) if best else None


def segment(sentence, literals):
    """문장을 [{t:'frame'|'slot', s:원문}] 으로 분해. 리터럴을 좌→우 순서로 찾는다.

    frame = 유저가 직접 놓아야 하는 부분, slot = 미리 주어지는 부분.
    슬롯이 하나도 없으면 치환할 게 없으므로 [3]이 성립하지 않는다.
    """
    s = sentence.strip()
    punct = ""
    m = re.search(r"[.?!]+$", s)
    if m:
        punct, s = m.group(0), s[: m.start()]
    segs, pos = [], 0
    for lit in literals:
        pat = re.compile(r"\b" + r"\s+".join(re.escape(w) for w in lit.split()) + r"\b", re.I)
        mm = pat.search(s, pos)
        if not mm:
            return None
        pre = s[pos : mm.start()].strip()
        if pre:
            segs.append({"t": "slot", "s": pre})
        segs.append({"t": "frame", "s": mm.group(0)})
        pos = mm.end()
    tail = s[pos:].strip()
    if tail:
        segs.append({"t": "slot", "s": tail})
    if not any(x["t"] == "slot" for x in segs):
        return None
    return {"segs": segs, "punct": punct}


def load_situations():
    """학습 문장(en) → {a_en, a_kr}. 파일이 없어도 빌드는 진행한다([5]만 비활성)."""
    if not SITUATIONS.exists():
        return {}
    raw = json.loads(SITUATIONS.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_vocab():
    if not VOCAB_CSV.exists():
        die(f"어휘 CSV 없음: {VOCAB_CSV} (VE_VOCAB_CSV로 지정)")
    out = {}
    for r in list(csv.reader(open(VOCAB_CSV, newline="", encoding="utf-8")))[1:]:
        if len(r) < 9 or not r[0].strip().isdigit():
            continue
        seq = int(r[0])
        if seq in out or r[8].strip() in VOCAB_FILTER_SKIP:
            continue
        ls, lsm = r[5].strip(), r[6].strip()
        if not (ls and lsm):
            continue
        out[seq] = {"spelling": r[2].strip(), "pos": (r[3].split("\n")[0]).strip(),
                    "meaning": clean_meaning(r[4]), "ls": ls, "lsm": lsm}
    return out


def load_gse():
    if not GSE_CSV.exists():
        die(f"gse CSV 없음: {GSE_CSV} (VE_GSE_CSV로 지정)")
    out = {}
    for r in list(csv.reader(open(GSE_CSV, newline="", encoding="utf-8")))[1:]:
        if len(r) < 15 or not r[3].strip().isdigit():
            continue
        seq = int(r[3])
        if seq not in out:
            lv = r[0].strip()
            out[seq] = {"level": int(lv) if lv.isdigit() else 0, "cefr": r[14].strip()}
    return out


def load_groups():
    if not EXPR_CSV.exists():
        die(f"표현 CSV 없음: {EXPR_CSV} (VE_EXPR_CSV로 지정)")
    rows = list(csv.reader(open(EXPR_CSV, newline="", encoding="utf-8")))[1:]
    groups, cur = OrderedDict(), None
    for r in rows:
        r = r + [""] * (12 - len(r))
        if r[0].strip():
            cur = r[0].strip()
            groups[cur] = {"trigger": r[1].strip(), "seq": r[2].strip(), "rank": r[5].strip(),
                           "pattern": r[8].strip(), "form": r[9].strip(),
                           "pmean": r[10].strip(), "pdesc": r[11].strip(), "sents": []}
        if cur and r[3].strip():
            groups[cur]["sents"].append({"en": r[3].strip(), "kr": r[4].strip()})
    return groups


def norm_word(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def merge_blanks(sent):
    """인접한 빈칸을 하나로 합친다 — 복합어가 쪼개진 경우.

    `[ice] [cream]` → `[ice cream]`, `[T]-[shirt]` → `[T-shirt]`.
    빈칸을 하나만 렌더하는 UI와도 맞아야 하므로 문장 문자열 자체를 고친다.
    """
    prev = None
    while prev != sent:
        prev = sent
        sent = re.sub(r"\[([^\]]+)\]([ \-]?)\[([^\]]+)\]",
                      lambda m: f"[{m.group(1)}{m.group(2)}{m.group(3)}]", sent)
    return sent


def same_word(a, b):
    return norm_word(a) == norm_word(b) or infl_match(a, b) or infl_match(b, a)


def make_vocab_a(v, trigger):
    """버전 A: 어휘 CSV의 learnSentence. 빈칸이 학습 대상 어휘를 가리켜야 한다.

    막아야 하는 건 **여러 단어짜리 표제어를 일부만 괄호친 예문**이다
    (`baggage claim`을 배우는데 빈칸이 `[baggage]`). 단일 단어 표제어의 빈칸은
    굴절형이어도(`child` → `[children]`) 그 어휘를 가리키므로 인정한다.
    """
    word = v["spelling"]
    ls = v["ls"]
    # 빈칸 병합은 합친 결과가 학습 어휘를 가리킬 때만 한다.
    # (`[ice] [cream]` → `ice cream` ✓ / `[went] [to]` → `went to` ✗ — 뒤 단어가 어휘가 아니다)
    merged = merge_blanks(ls)
    mm = BRACKET.search(merged)
    if mm and (same_word(mm.group(1).strip(), word) or same_word(mm.group(1).strip(), trigger)):
        ls = merged
    m = BRACKET.search(ls)
    if not m:
        return None
    ans = m.group(1).strip()
    if not (same_word(ans, word) or same_word(ans, trigger)):
        if len(word.split()) > 1 or len(str(trigger).split()) > 1:
            return None
    # 합친 뒤에도 빈칸이 둘 이상이면 UI가 첫 빈칸만 입력칸으로 만들어 나머지가 대괄호로 남는다
    if len(BRACKET.findall(ls)) > 1:
        return None
    return {"answer": ans,
            "enLines": [x.strip() for x in ls.split("\n")],
            "koLines": [x.strip() for x in v["lsm"].split("\n")]}


def main():
    vocab, gse, groups = load_vocab(), load_gse(), load_groups()
    situations = load_situations()
    items, skipped = [], {"조인실패": 0, "버전A불가": 0, "버전B불가": 0, "문장부족": 0,
                          "공통프레임없음": 0, "문법틀form": 0, "프레임≠form": 0}

    for g in groups.values():
        if not g["seq"].isdigit() or len(g["sents"]) < 1:
            skipped["문장부족"] += 1
            continue
        seq = int(g["seq"])
        v = vocab.get(seq)
        if v is None:
            skipped["조인실패"] += 1
            continue

        va = make_vocab_a(v, g["trigger"])
        if va is None:
            skipped["버전A불가"] += 1
            continue

        # [3]은 어휘 표현에만 성립한다 — 문법 틀은 표현 경계가 정해지지 않는다
        if not lexical_form(g["form"] or g["pattern"]):
            skipped["문법틀form"] += 1
            continue

        # [3] 슬롯 치환: 학습 문장에서 공통 프레임을 추출한다(문장1 포함 필수)
        sents = [x["en"] for x in g["sents"]]
        found = extract_frame(sents)
        if found is None:
            skipped["공통프레임없음"] += 1
            continue
        lits, cov = found
        if not frame_matches_form(lits, g["form"] or g["pattern"]):
            skipped["프레임≠form"] += 1
            continue
        # 프레임이 실제로 들어있는 문장만 [3]에 쓴다. cov[0]은 항상 문장1.
        segd = {i: segment(sents[i], lits) for i in cov}

        s1 = g["sents"][0]
        blanked = blank_trigger(s1["en"], g["trigger"])
        if blanked is None:
            skipped["버전B불가"] += 1
            continue
        b_en, b_ans = blanked
        b_kr = mark_meaning_kr(s1["kr"], v["meaning"], v["lsm"])

        meta = gse.get(seq, {})
        items.append({
            "trigger": g["trigger"],
            "word": v["spelling"],
            "meaning": v["meaning"],
            "pos": v["pos"],
            "cefr": meta.get("cefr", ""),
            "level": meta.get("level", 0),
            "rank": int(g["rank"]) if g["rank"].isdigit() else 10 ** 9,
            # 버전 A — 어휘 문장과 표현 문장이 서로 다름
            "vocabA": va,
            # 버전 B — 표현 문장 자체로 어휘를 배움(트리거 자리를 빈칸으로)
            # 번역문에서 정답 뜻을 찾으면 초록 마크업으로, 못 찾으면 별도 힌트 줄로
            "vocabB": {"answer": b_ans, "enLines": [b_en],
                       "koLines": [b_kr or s1["kr"]],
                       "hint": "" if b_kr else short_meaning(v["meaning"])},
            "sentence": {"en": s1["en"], "kr": s1["kr"], "trigger": g["trigger"]},
            "pattern": {"form": g["form"] or g["pattern"], "meaning": g["pmean"], "desc": g["pdesc"]},
            # [3] 처음 보는 문장에 같은 프레임을 직접 써보는 단계.
            # 프레임을 공유하는 문장만 담으므로 문항에 따라 1개 또는 여러 개다
            # (2개 이상이면 [3]이 2회차까지 진행된다).
            "frame": lits,
            "situation": situations.get(s1["en"]),
            "traps": [],
            "_trapSent": sents[cov[1]] if len(cov) > 1 else sents[0],
            "baseSegs": segd[0]["segs"],
            "apply": [{"en": g["sents"][i]["en"], "kr": g["sents"][i]["kr"], **segd[i]}
                      for i in cov[1:]],
            "siblings": g["sents"][1:3],
        })

    items.sort(key=lambda x: (x["rank"], x["level"]))
    if MAX_ITEMS:
        items = items[:MAX_ITEMS]

    # 함정 후보 풀 — 채택된 프레임들의 내용어. 전체를 모은 뒤에야 만들 수 있다.
    seen_pool = set()
    for it in items:
        for lit in it["frame"]:
            for w in lit.split():
                wl = w.lower()
                if wl not in FUNCTION_WORDS and wl.isalpha() and len(wl) >= 3 and wl not in seen_pool:
                    seen_pool.add(wl)
                    CONTENT_TRAP_POOL.append(wl)
    CONTENT_TRAP_POOL.sort()
    for it in items:
        it["traps"] = make_traps(it["frame"], it.pop("_trapSent"))

    data = {
        "meta": {
            "type": "vocab-expression",
            "note": "한 문항 = 트리거 어휘 + 그 어휘가 트리거한 표현 문장. "
                    "버전 A는 어휘 문장과 표현 문장이 다르고, 버전 B는 표현 문장으로 어휘를 배운다.",
            "versions": {"a": "어휘 문장 ≠ 표현 문장", "b": "표현 문장으로 어휘 학습"},
            "flow": "[1] 어휘 빈칸 → [2] 같은 문장 배열 → [3] 처음 보는 문장에 프레임 직접 쓰기",
            "maxItems": MAX_ITEMS,
        },
        "items": items,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_vocab_expression] 완료 → {OUT}")
    print(f"  후보 그룹 {len(groups)} → 사용 {len(items)}문항 | 제외: {skipped}")
    print(f"  [5] 상황 대사가 붙은 문항: {len([x for x in items if x.get('situation')])}")


if __name__ == "__main__":
    main()
