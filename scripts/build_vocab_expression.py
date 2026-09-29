#!/usr/bin/env python3
"""어휘→표현 프로토타입 데이터 생성 (버전 A/B 공용).

소스(레포 밖, 기본값은 ~/Downloads):
  - 문장 CSV: `표현데이터_재작업_전체900 - 문장` — **문장 한 줄 = 한 행**. 유닛(`유닛`)당
    S1(학습 문장) + S2~S5 + 선택적 U1~U3(주어 변형)·X1~X2(확장). 프레임이 대괄호로
    저작돼 있다: `[Talk to] your parents.` / `부모님[이랑 얘기해] 봐.` (`뼈대` 열 = form)
  - 표현 CSV: `유기적 통합모드 문장 (공유용)` — 트리거 어휘(`trigger`,`trigger_dictseq`)와
    결과 카드(형태/뜻/설명). **문장은 읽지 않고** `유닛`=`id`로 조인만 한다
  - 어휘 CSV(All_*.csv): seq(=dictSeq) → learnSentence(영어 예문, [단어]=빈칸 정답)
    + learnSentenceMeaning(한국어 번역, [뜻]=초록) + meaning + pos
  - gse CSV: dictSeq → 어휘 레벨(1~30) + CEFR

두 버전이 같은 문항을 써야 비교가 되므로 **양쪽 모두 성립하는 유닛만** 남긴다.
  - 버전 A: 어휘 학습 문장 = 어휘 CSV의 learnSentence (표현 문장과 다른 문장)
  - 버전 B: 어휘 학습 문장 = 학습 문장(S1)에서 트리거 어휘를 빈칸으로

프레임·슬롯(`frame`·`baseSegs`·`apply`)과 한국어 표현 구간(`krMark`)은 **저작 데이터를
그대로** 쓴다 — 대괄호 위치가 곧 경계라 문장에서 리터럴을 되찾지 않는다. 응용 문장은
S1과 프레임 조각이 **같은 것만** 담는다(주어가 바뀐 변형은 앱의 리터럴 기준 채점과 어긋난다).

출력: public/vocab-expression.data.json (커밋되는 생성물). 손으로 편집하지 말 것.
"""
import csv, json, os, re, sys
from collections import OrderedDict
from pathlib import Path

DL = Path.home() / "Downloads"
# 문장·프레임의 소스. 프레임과 한국어 표현 구간이 대괄호로 저작돼 있다.
SENT_CSV  = Path(os.environ.get("VE_SENT_CSV",  DL / "표현데이터_재작업_전체900 - 문장.csv"))
# 트리거 어휘·결과 카드(뜻/설명)의 소스. 문장은 여기서 읽지 않고 `유닛`=`id`로 조인만 한다.
EXPR_CSV  = Path(os.environ.get("VE_EXPR_CSV",  DL / "유기적 통합모드 문장 (공유용) - 문장1 변형후보 추가 (검토중).csv"))
VOCAB_CSV = Path(os.environ.get("VE_VOCAB_CSV", DL / "All_(2026-09-01_20_14_12).csv"))
GSE_CSV   = Path(os.environ.get("VE_GSE_CSV",   DL / "gse_corrected_final_0624 - 보정결과_전체.csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "vocab-expression.data.json"
# [5] 상황 단계용 A 대사 — 소스 CSV에 상황 필드가 없어 손으로 적은 프로토타입 문안
SITUATIONS = Path(__file__).resolve().parent / "vocab_expression_situations.json"
# [4] 말해보기 옵션 B용 A 대사 — 그 문장이 짧은 답이 되는 질문. 손으로 적은 프로토타입 문안
QUESTIONS = Path(__file__).resolve().parent / "vocab_expression_questions.json"
# [4] 방식 D — 내 차례 **뒤**에 오는 A의 반응(앞 대사는 QUESTIONS)
REPLIES = Path(__file__).resolve().parent / "vocab_expression_replies.json"

MAX_ITEMS = int(os.environ.get("VE_MAX_ITEMS", "0"))    # 0이면 전체
VOCAB_FILTER_SKIP = {"sexual", "unnecessary"}
BRACKET = re.compile(r"\[([^\]]+)\]")
INFL = re.compile(r"^(?:s|es|ed|d|ing|er|est|ies|ier|iest|'s|')$")


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


def load_questions():
    """영어 문장(en) → {en, kr}. 학습 문장과 말해보기 대상 문장 양쪽 키가 들어 있다."""
    if not QUESTIONS.exists():
        return {}
    raw = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    return {k: {"en": v[0], "kr": v[1]} for k, v in raw.items() if not k.startswith("_")}


def load_replies():
    """영어 문장(en) → {en, kr}. [4] 방식 D가 **내 차례 뒤에 오는 A의 반응**으로 쓴다.
    파일이 없어도 빌드는 진행한다(그 문항에서 D만 비활성)."""
    if not REPLIES.exists():
        return {}
    raw = json.loads(REPLIES.read_text(encoding="utf-8"))
    return {k: {"en": v[0], "kr": v[1]} for k, v in raw.items() if not k.startswith("_")}


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


# 표현 CSV는 **열 이름으로** 읽는다 — 시트마다 열 순서가 다르고 열이 늘기도 한다
# (`표제어 또는 회화패턴`이 9번째였다가 2번째로 오고, `jl 검토`가 뒤에 붙었다).
# 인덱스로 읽으면 조용히 엉뚱한 열을 집어 트리거와 문장이 뒤바뀐다.
EXPR_COLS = {"id": ("id",), "trigger": ("trigger",), "seq": ("trigger_dictseq",),
             "rank": ("trigger_newRank3",), "en": ("sentence",), "kr": ("translation",),
             "pattern": ("표제어 또는 회화패턴",), "form": ("카드 초록 (형태)", "카드 초록(형태)"),
             "pmean": ("카드 회색 1행 (뜻)", "카드 회색1행 (뜻)"),
             "pdesc": ("카드 회색 2행 (설명)", "카드 회색2행 (설명)")}


# 문장 CSV는 **문장 한 줄 = 한 행**이고 프레임이 대괄호로 저작돼 있다
# (`[Talk to] your parents.` / `부모님[이랑 얘기해] 봐.`). 그래서 이 빌드는 프레임을
# 추론하지 않는다 — 공통 구간을 difflib 로 뽑고 `form`과 대조해 걸러내던 계층 전체가
# 저작 데이터로 대체됐다(영어·한국어 마크업 5,740행 전부 존재).
# 열은 **이름으로** 찾는다(`EXPR_COLS`와 같은 이유) — 소스에 열이 늘면 위치 기반 파싱은
# 조용히 다른 열을 읽는다.
SENT_COLS = {"unit": ("유닛",), "form": ("뼈대",), "role": ("역할",),
             "en": ("문장 (빨강 = 트리거)", "문장(빨강 = 트리거)", "문장"),
             "kr": ("번역",), "shape": ("문형",), "check": ("확인 필요",)}


def sig(lits):
    return tuple(x.lower().strip() for x in lits)


def parse_marked(s):
    """`[Talk to] your parents.` → (`Talk to your parents.`, ['Talk to'], segs, punct).

    대괄호가 프레임, 나머지가 슬롯이다. **위치를 그대로 읽으므로** 리터럴을 문장에서
    다시 찾지 않는다(`segment`가 하던 일) — 같은 낱말이 슬롯에도 있는 문장에서
    엉뚱한 자리를 프레임으로 집는 일이 없다.
    """
    s = (s or "").strip()
    lits, segs, pos = [], [], 0
    for m in BRACKET.finditer(s):
        pre = s[pos:m.start()]
        if pre.strip():
            segs.append({"t": "slot", "s": pre.strip()})
        lit = m.group(1).strip()
        lits.append(lit)
        segs.append({"t": "frame", "s": lit})
        pos = m.end()
    tail = s[pos:]
    plain = BRACKET.sub(lambda m: m.group(1), s)
    plain = re.sub(r"\s+", " ", plain).strip()
    punct = ""
    mm = re.search(r"[.?!]+$", tail.strip())
    if mm:
        punct = mm.group(0)
        tail = tail.strip()[: mm.start()]
    if tail.strip():
        segs.append({"t": "slot", "s": tail.strip()})
    return plain, lits, segs, punct


def load_sentences():
    """문장 CSV를 유닛별로 묶는다. 유닛당 S1이 학습 문장이고 나머지는 응용 문장이다."""
    if not SENT_CSV.exists():
        die(f"문장 CSV 없음: {SENT_CSV} (VE_SENT_CSV로 지정)")
    rows = list(csv.reader(open(SENT_CSV, newline="", encoding="utf-8-sig")))
    head = [c.strip() for c in rows[0]]
    idx = {}
    for key, names in SENT_COLS.items():
        for n in names:
            if n in head:
                idx[key] = head.index(n)
                break
        else:
            die(f"문장 CSV에 열이 없음: {key} ({' / '.join(names)}) — 실제 헤더: {head}")
    get = lambda r, k: (r[idx[k]].strip() if idx[k] < len(r) else "")
    units = OrderedDict()
    for r in rows[1:]:
        u = get(r, "unit")
        if not u or not get(r, "en"):
            continue
        plain, lits, segs, punct = parse_marked(get(r, "en"))
        kr_mark = get(r, "kr")
        units.setdefault(u, {"unit": u, "form": get(r, "form"), "sents": []})
        units[u]["sents"].append({
            "role": get(r, "role"), "en": plain, "lits": lits,
            "segs": segs, "punct": punct,
            # 한국어 표현 구간도 저작돼 있다 — `krMark`가 곧 소스 문자열이다
            "kr": BRACKET.sub(lambda m: m.group(1), kr_mark).strip(),
            "krMark": kr_mark,
        })
    return units


def load_meta():
    """트리거 어휘·결과 카드를 `id`별로 읽는다. 문장은 `load_sentences`가 읽는다.

    그룹 첫 행에만 값이 있어 forward-fill 하고, 문장 CSV 의 유닛이 갈라진 경우
    (`10013-1`~`10013-4`가 기존 `10013` 하나에서 나왔다) **접미사를 떼고** 조인한다.
    """
    if not EXPR_CSV.exists():
        die(f"표현 CSV 없음: {EXPR_CSV} (VE_EXPR_CSV로 지정)")
    rows = list(csv.reader(open(EXPR_CSV, newline="", encoding="utf-8-sig")))
    head = [c.strip() for c in rows[0]]
    idx = {}
    for key, names in EXPR_COLS.items():
        for n in names:
            if n in head:
                idx[key] = head.index(n)
                break
        else:
            die(f"표현 CSV에 열이 없음: {key} ({' / '.join(names)}) — 실제 헤더: {head}")
    get = lambda r, k: (r[idx[k]].strip() if idx[k] < len(r) else "")
    out, cur = OrderedDict(), None
    for r in rows[1:]:
        if get(r, "id"):
            cur = get(r, "id")
            out[cur] = {"trigger": get(r, "trigger"), "seq": get(r, "seq"), "rank": get(r, "rank"),
                        "pattern": get(r, "pattern"), "form": get(r, "form"),
                        "pmean": get(r, "pmean"), "pdesc": get(r, "pdesc")}
    return out


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
    vocab, gse = load_vocab(), load_gse()
    meta = load_meta()
    units = load_sentences()
    situations = load_situations()
    questions = load_questions()
    replies = load_replies()
    items, skipped = [], {"메타없음": 0, "조인실패": 0, "버전A불가": 0, "버전B불가": 0,
                          "프레임없음": 0, "슬롯없음": 0}
    dropped_variants = 0

    for u, g in units.items():
        # 문장 CSV 에는 트리거 어휘가 없다 — 기존 표현 CSV 와 `유닛`=`id`로 조인한다.
        # 유닛이 갈라진 경우(`10013-1`)는 접미사를 떼고 원래 그룹을 찾는다.
        m = meta.get(u) or meta.get(u.split("-")[0])
        if not m or not m["trigger"] or not m["seq"].isdigit():
            skipped["메타없음"] += 1
            continue
        seq = int(m["seq"])
        v = vocab.get(seq)
        if v is None:
            skipped["조인실패"] += 1
            continue

        va = make_vocab_a(v, m["trigger"])
        if va is None:
            skipped["버전A불가"] += 1
            continue

        s1 = next((x for x in g["sents"] if x["role"] == "S1"), g["sents"][0])
        lits = s1["lits"]
        if not lits:
            skipped["프레임없음"] += 1
            continue
        # 슬롯이 없으면 [2]에서 회색으로 줄 것이 없다(문장 전체가 표현인 경우)
        if not any(x["t"] == "slot" for x in s1["segs"]):
            skipped["슬롯없음"] += 1
            continue

        blanked = blank_trigger(s1["en"], m["trigger"])
        if blanked is None:
            skipped["버전B불가"] += 1
            continue
        b_en, b_ans = blanked
        b_kr = mark_meaning_kr(s1["kr"], v["meaning"], v["lsm"])

        # 응용 문장은 **S1과 프레임이 같은 것만** 쓴다. 같은 유닛에는 주어가 바뀐 변형도
        # 들어 있는데(`I didn't` → `She didn't`), 앱의 프레임 채점·초록 표기가 리터럴
        # 기준이라 그것을 대상으로 쓰면 맞는 답을 틀렸다고 하게 된다.
        fam = [x for x in g["sents"] if x is not s1 and sig(x["lits"]) == sig(lits)
               and any(t["t"] == "slot" for t in x["segs"])]
        dropped_variants += len(g["sents"]) - 1 - len(fam)

        gmeta = gse.get(seq, {})
        items.append({
            "trigger": m["trigger"],
            "word": v["spelling"],
            "meaning": v["meaning"],
            "pos": v["pos"],
            "cefr": gmeta.get("cefr", ""),
            "level": gmeta.get("level", 0),
            "rank": int(m["rank"]) if m["rank"].isdigit() else 10 ** 9,
            # 버전 A — 어휘 문장과 표현 문장이 서로 다름
            "vocabA": va,
            # 버전 B — 표현 문장 자체로 어휘를 배움(트리거 자리를 빈칸으로)
            "vocabB": {"answer": b_ans, "enLines": [b_en],
                       "koLines": [b_kr or s1["kr"]],
                       "hint": "" if b_kr else short_meaning(v["meaning"])},
            # 한국어 표현 구간(`krMark`)은 저작 데이터다 — 뜻 문자열로 되짚지 않는다
            "sentence": {"en": s1["en"], "kr": s1["kr"], "trigger": m["trigger"],
                         "krMark": s1["krMark"]},
            "pattern": {"form": g["form"] or m["form"] or m["pattern"],
                        "meaning": m["pmean"], "desc": m["pdesc"]},
            "frame": lits,
            "situation": situations.get(s1["en"]),
            "ask": questions.get(s1["en"]),
            "reply": replies.get(s1["en"]),
            "traps": [],
            "_trapSent": fam[0]["en"] if fam else s1["en"],
            "baseSegs": s1["segs"],
            "apply": [{"en": x["en"], "kr": x["kr"], "segs": x["segs"], "punct": x["punct"],
                       "krMark": x["krMark"],
                       "ask": questions.get(x["en"]),
                       "reply": replies.get(x["en"])}
                      for x in fam],
            "siblings": [{"en": x["en"], "kr": x["kr"], "krMark": x["krMark"]}
                         for x in fam[:2]],
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
            "flow": "[1] 어휘 빈칸 → 인식 → [2] 표현 넣기 → [3] 문장 전체 → [4] 말해보기",
            "maxItems": MAX_ITEMS,
        },
        "items": items,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ap = [len(x["apply"]) for x in items]
    print(f"[build_vocab_expression] 완료 → {OUT}")
    print(f"  문장 CSV 유닛 {len(units)} → 사용 {len(items)}문항 | 제외: {skipped}")
    print(f"  응용 문장 {sum(ap)}개(문항당 중앙값 {sorted(ap)[len(ap)//2] if ap else 0}) | "
          f"프레임이 달라 제외한 변형 문장 {dropped_variants}개")
    print(f"  표현 뜻(krMark) 있는 문항: {len([x for x in items if x['sentence']['krMark'] != x['sentence']['kr']])}")
    print(f"  [4] 질문이 붙은 문항: {len([x for x in items if x.get('ask')])}")
    print(f"  [5] 상황 대사가 붙은 문항: {len([x for x in items if x.get('situation')])}")


if __name__ == "__main__":
    main()
