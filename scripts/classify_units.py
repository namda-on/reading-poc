#!/usr/bin/env python3
"""표현 유닛을 학습 유형(패턴형·변화형·대비형·자리형)으로 분류한다.

소스(레포 밖): UNITS_CSV, 기본 ~/Downloads/유기적 통합모드 문장 (공유용) - 문장1 변형후보 추가 (검토중)-문장만 확정.csv
산출: public/vocab-expression-units.gen.json

유닛은 '학습자가 문장을 만들 때 내려야 하는 결정 하나'다. 그 결정이 무엇인지는
유닛 안 문장들의 대괄호에서 **무엇이 고정이고 무엇이 바뀌는가**로 정한다.
  - 패턴형: 대괄호가 모든 문장에서 같다(굴절·주어·축약만 다름)          → 결정 없음, 덩어리를 기억
  - 변화형: 바뀌는 낱말이 문장마다 다르지만 같은 꼴(-ed·-ing·-est·-er)로 바뀐다 → 규칙을 적용
  - 대비형: 바뀌는 자리에 몇 개 안 되는 선택지가 번갈아 온다(-ing/to, at/on/in) → 뜻으로 고른다
  - 자리형: 번갈아 오는 것이 빈도·정도 부사다(always/usually/never)       → 자리를 정한다
판정에는 S1의 주어 변형(문장1-2·1-3)을 쓰지 않는다 — 주어만 바꾼 같은 문장이라 무엇이 반복되는지를 부풀린다.
"""
import csv, json, os, re, sys
from collections import Counter, OrderedDict
from pathlib import Path

DL = Path.home() / "Downloads"
SRC = Path(os.environ.get("UNITS_CSV", DL / "유기적 통합모드 문장 (공유용) - 문장1 변형후보 추가 (검토중)-문장만 확정.csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "vocab-expression-units.gen.json"

# 규칙이 데이터와 어긋나는 유닛 — 사람이 정한 값과 그 이유. 규칙을 고치기 전까지 여기서 덮는다.
OVERRIDES = {
    "10084": ("해당없음", "4형식 어순(동사+사람+물건) — 바뀌는 것이 동사 자체라 고정부도 선택지도 없다"),
    "10395": ("해당없음", "관계부사 생략 — 학습 대상이 '빠진 낱말'이라 짚을 것이 없다"),
    "10405": ("해당없음", "목적격 관계대명사 생략 — 학습 대상이 '빠진 낱말'이라 짚을 것이 없다"),
    "10061": ("해당없음", "시각 읽기(four fifteen) — 틀도 규칙도 없는 숫자 읽기"),
    "10107": ("해당없음", "keep/make/find + 목적어 + 형용사 어순 — 괄호가 형용사를 덮지 않아 자리를 짚을 수 없다"),
    "10028": ("자리형", "동사 + 부사(well · fast · carefully) — 부사가 열린 목록이라 규칙의 부사 목록에 없다"),
    "10030": ("자리형", "동사 + 부사(early · late · hard) — 부사가 열린 목록이라 규칙의 부사 목록에 없다"),
    "10132": ("자리형", "대명사는 동사와 부사 사이(pick it up) — 부사가 달라지는 건 구동사가 달라서다"),
    "10328": ("자리형", "분리형 구동사(turn ~ on) — 부사가 달라지는 건 구동사가 달라서다"),
    "10365": ("자리형", "something + 형용사 — 형용사가 뒤에 오는 자리가 핵심"),
    "10357": ("패턴형", "How about / What about 은 같은 뜻 — 고를 게 없다"),
    "10344": ("변화형", "숫자-단위 하이픈(fifteen-week) — 단위에 -s 를 붙이지 않는 꼴 바꾸기. 하이픈 낱말이라 규칙의 어미 판정에 걸리지 않는다"),
    "10060": ("대비형", "mine / yours / his / hers — his 가 인칭대명사로 걸러져 규칙이 선택지를 놓친다"),
}

PERS = set("i you he she it we they me him her us them my your his our their its".split())
BE = set("am is are was were be been being".split())
DO = set("do does did".split())
HAVE = set("have has had".split())
MODAL = set("will would can could shall should may might must".split())
NEG = {"not"}
POS_ADV = set("always usually often sometimes never rarely seldom ever very really pretty so too quite already still even just also".split())
FUNC = POS_ADV | set("""at on in to for from with by of about after before under over into onto out up down off away back around through
across along a an the this that these those some any each every all both either neither no few little many much more most less least
another other and or but because if when while until since though although as than which who whom whose where why how what whatever
whoever whichever however wherever whenever mine yours hers ours theirs myself yourself himself herself itself ourselves themselves
there let once twice""".split())
CONTR = {"won't": ["will", "not"], "can't": ["can", "not"], "cannot": ["can", "not"], "let's": ["let", "us"]}
ORD = set("first second third fifth eighth ninth twelfth".split())
IS_HOST = set("that what where who how here there it let this everyone everything everybody nothing something someone".split())
IRR = {'went':'go','gone':'go','met':'meet','lost':'lose','caught':'catch','grew':'grow','sent':'send','got':'get','gotten':'get',
 'made':'make','took':'take','taken':'take','gave':'give','given':'give','came':'come','saw':'see','seen':'see','found':'find',
 'told':'tell','said':'say','broke':'break','broken':'break','ate':'eat','eaten':'eat','left':'leave','kept':'keep','sat':'sit',
 'ran':'run','became':'become','brought':'bring','bought':'buy','thought':'think','felt':'feel','held':'hold','spent':'spend',
 'wore':'wear','worn':'wear','won':'win','fell':'fall','fallen':'fall','knew':'know','known':'know','done':'do','began':'begin','paid':'pay',
 'heard':'hear','built':'build','taught':'teach','woke':'wake','chose':'choose','drove':'drive','wrote':'write','written':'write',
 'spoke':'speak','stood':'stand','understood':'understand','slept':'sleep','threw':'throw','forgot':'forget','shook':'shake',
 'drew':'draw','led':'lead','meant':'mean','sold':'sell','shot':'shoot','stole':'steal','stolen':'steal','bit':'bite',
 'bitten':'bite','hid':'hide','rode':'ride','flew':'fly','sang':'sing','swam':'swim','fed':'feed','fought':'fight','sped':'speed',
 'stuck':'stick','tore':'tear','froze':'freeze','rose':'rise','blew':'blow','lent':'lend','dealt':'deal','hung':'hang','read':'read'}
IRR_CMP = {'better':'good','best':'good','worse':'bad','worst':'bad'}

def die(msg):
    print("error:", msg, file=sys.stderr); sys.exit(1)

def stem(w):
    """같은 유닛 안에서 같은 낱말인지만 가리면 되므로 사전형을 되살리지 않고 일관되게 깎는다
    (line·lining → lin, die·died·dies → di, cry·cried → cri). 불규칙형은 표로 원형에 붙인다."""
    w = IRR.get(w, IRR_CMP.get(w, w))
    for suf in ("ing", "ied", "ies", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            w = w[:-len(suf)] + ("i" if suf in ("ied", "ies") else ""); break
    if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "ls": w = w[:-1]
    if w.endswith("y"): w = w[:-1] + "i"
    if w.endswith("e") and len(w) > 2: w = w[:-1]
    return w

def tokens(sentence):
    """대괄호 안 낱말 → [(표면형, 분류)] — 분류는 PERS/BE/DO/HAVE/MODAL/NEG/FUNC/OPEN"""
    out = []
    for part in re.findall(r"\[([^\]]+)\]", sentence):
        for raw in part.lower().replace("’", "'").split():
            w = re.sub(r"[^a-z'\-]", "", raw).strip("'")
            if not w: continue
            pieces = CONTR.get(w)
            if not pieces:
                m = re.match(r"^(.+?)(n't|'s|'m|'re|'ll|'d|'ve)$", w)
                if m:
                    head, tail = m.groups()
                    head = {"ca": "can", "wo": "will", "sha": "shall"}.get(head, head)
                    if tail == "'s" and head not in PERS | IS_HOST:
                        pieces = [head, "'s"]
                    else:
                        pieces = [head, {"n't": "not", "'s": "is", "'m": "am", "'re": "are", "'ll": "will", "'d": "would", "'ve": "have"}[tail]]
                else:
                    pieces = [w]
            for p in pieces:
                if p == "'s": c = "POSS"
                elif p in PERS: c = "PERS"
                elif p in BE: c = "BE"
                elif p in DO: c = "DO"
                elif p in HAVE: c = "HAVE"
                elif p in MODAL: c = "MODAL"
                elif p in NEG: c = "NEG"
                elif p in FUNC: c = "FUNC"
                else: c = "OPEN"
                out.append((p, c))
    return out

def shape_of(toks):
    """바뀌는 꼴 — 열린 낱말은 어미로만 남긴다(opened → V-ed). 주어·소유격은 버린다"""
    sh = []
    for i, (w, c) in enumerate(toks):
        if c == "PERS": continue
        if c == "POSS": sh.append("N-'s"); continue
        if c in ("BE", "DO", "HAVE", "MODAL", "NEG"): sh.append(c); continue
        if c == "FUNC": sh.append(w); continue
        nxt = toks[i + 1][0] if i + 1 < len(toks) else ""
        if w.endswith("ing") and len(w) > 4: sh.append("V-ing")
        elif w in IRR or (w.endswith("ed") and len(w) > 3): sh.append("V-ed")
        elif w in ORD or re.fullmatch(r"\w+-(first|second|third|\w+th)|\w{3,}th", w) and w not in ("both", "with", "month", "truth", "health", "earth", "south", "north", "youth", "tooth", "mouth", "death", "path", "bath", "math", "cloth", "faith", "length", "strength", "depth", "width", "booth", "growth", "warmth", "breath"): sh.append("ORD")
        elif (w.endswith("est") and len(w) > 4) or w in ("best", "worst"): sh.append("A-est")
        elif (w.endswith("er") and len(w) > 3 and (nxt in ("than", "and") or (i and toks[i - 1][0] == "the"))) or w in ("better", "worse"): sh.append("A-er")
        else: sh.append("W")
    return tuple(sh)

def key_of(toks):
    """같은 덩어리인가 — 열린 낱말은 원형으로, 주어·조동사 차이는 무시한다"""
    return tuple(stem(w) if c == "OPEN" else (c if c in ("BE", "DO", "HAVE", "POSS") else w)
                 for w, c in toks if c != "PERS")

FORM = {"V-ing", "V-ed", "A-est", "A-er", "N-'s", "ORD"}
ARTICLE = {"a", "an", "the"}

def form_classes(toks):
    """문장이 쓰는 꼴 — to + 원형은 `to-V` 로 따로 센다(stop to buy)"""
    sh = shape_of(toks)
    out = {x for x in sh if x in FORM}
    if any(a == "to" and b == "W" for a, b in zip(sh, sh[1:])): out.add("to-V")
    return out

# 카드 초록(형태)에 형태 변화가 적혀 있는가 — 시제 때문에 우연히 생긴 -ed/-ing 를 학습 대상으로 착각하지 않게 한다
FORM_HINT = re.compile(r"-ing|_ing|-ed|_ed|_est|_er|er than|과거|분사|복수|단수|서수|원형|[_ ]['’]s\b")

def classify(indep, form):
    """판정 순서가 곧 규칙이다 — 앞 단계에서 걸리면 뒤는 보지 않는다.
    1 대괄호가 모두 같은 덩어리                    → 패턴형
      같은 낱말이 시제·생략만 다름                   → 패턴형 (went out / going out)
    2 서로 다른 꼴이 번갈아 온다                     → 대비형 (-ing / to, -ing / -ed)
    3 모두 같은 꼴, 낱말은 제각각                    → 변화형 (-ed, -est, -er, -ing, 's, 서수)
    4 문장마다 빈도·정도 부사가 하나씩, 종류가 둘 이상 → 자리형 (always / usually / never)
      기능어가 번갈아 온다                           → 대비형 (at / on / in, can / could, some / any)
    5 공통 낱말이 남는다                            → 패턴형 (괄호 안에 슬롯 낱말이 함께 들어 있다)
    6 첫 낱말(동사 등)이 몇 개 안에서 번갈아 온다       → 대비형 (become / get / turn, look / sound / feel)
    7 절반 이상 문장에 남는 낱말이 있다               → 패턴형 (나머지 문장은 괄호가 다르게 쳐졌다)
    2·3 은 카드 초록에 형태 변화가 적혀 있을 때만 인정한다 — 시제 때문에 우연히 생긴 -ed/-ing 를 학습 대상으로 착각하지 않게.
    '번갈아 온다'는 둘 이상이 쓰이고 한쪽이 80%를 넘게 독차지하지 않을 때다 — 한 번 섞인 변형(would 사이의 could)은 선택지가 아니다.
    be·do·have 의 주어 일치(is/are, do/does)는 결정으로 보지 않는다 — 주어가 정해 주는 것이라 고를 게 없다."""
    n = len(indep)
    hint = bool(FORM_HINT.search(form))
    toks = [tokens(e) for _, e, _ in indep]
    keys = [key_of(t) for t in toks]
    if len(set(keys)) == 1:
        return "패턴형", "모든 문장의 대괄호가 같은 덩어리", " ".join(keys[0]), {"같은 덩어리": n}, ["같은 덩어리"] * n

    opens = [tuple(sorted(stem(w) for w, c in t if c == "OPEN")) for t in toks]
    o_mode, o_cnt = Counter(opens).most_common(1)[0]
    if o_mode and o_cnt / n >= 0.6:
        return "패턴형", "같은 낱말이 활용·생략만 다름: " + " ".join(o_mode), " ".join(o_mode), {"같은 덩어리": o_cnt}, ["같은 덩어리" if o == o_mode else None for o in opens]

    fc = [form_classes(t) for t in toks]
    single = [next(iter(f)) for f in fc if len(f) == 1]
    only = Counter(single)
    if hint and len(only) >= 2 and len(single) / n >= 0.8 and max(only.values()) / len(single) <= 0.8:
        return "대비형", "번갈아 오는 꼴: " + " / ".join(sorted(only)), " / ".join(sorted(only)), dict(only), [next(iter(f)) if len(f) == 1 else None for f in fc]

    def choice(picks):
        """번갈아 오는 선택지인가 — 둘 이상이 쓰이고, 한쪽이 80%를 넘게 독차지하지 않는다
        (If I were ~, I would ~ 에 could 가 한 번 섞인 것은 선택지가 아니다)"""
        c = Counter(picks)
        return len(c) >= 2 and len(picks) / n >= 0.7 and max(c.values()) / len(picks) <= 0.8 and max(c.values()) >= 2

    used = Counter(x for f in fc for x in f)
    top, cnt = (used.most_common(1)[0] if used else (None, 0))
    form_common = hint and top and cnt / n >= 0.6 and len(set(opens)) >= 2
    if form_common:
        return "변화형", "바뀌는 낱말은 제각각, 꼴은 같음: " + top, top, {top: len({o for o, f in zip(opens, fc) if top in f})}, [top if top in f else None for f in fc]

    lits = [set(w for w, c in t if c in ("FUNC", "MODAL") and w not in ARTICLE) for t in toks]
    every = set.intersection(*lits)
    seen = Counter(x for l in lits for x in l)
    alt = {x for x in set().union(*lits) - every if seen[x] / n < 0.8}
    # 한 문장에 둘이 겹치면(some more time) 유닛 전체에서 더 자주 나온 쪽을 그 문장의 선택으로 본다
    picks = [max(l & alt, key=lambda x: (seen[x], x)) for l in lits if l & alt]
    advs = [l & POS_ADV for l in lits]
    one_adv = [next(iter(a)) for a in advs if len(a) == 1]
    if len(set(one_adv)) >= 2 and len(one_adv) / n >= 0.8:
        A = sorted(set(one_adv))
        return "자리형", "갈아 끼워지는 부사: " + " / ".join(A), " / ".join(A), dict(Counter(one_adv)), [next(iter(a)) if len(a) == 1 else None for a in advs]
    if choice(picks):
        A = sorted(set(picks))
        return "대비형", "갈아 끼워지는 낱말: " + " / ".join(A), " / ".join(A), dict(Counter(picks)), [max(l & alt, key=lambda x: (seen[x], x)) if l & alt else None for l in lits]

    common = Counter(keys[0])
    for k in keys[1:]: common &= Counter(k)
    if common:
        core = " ".join(common.elements())
        return "패턴형", "고정부 " + core + " + 괄호 안 슬롯", core, {"같은 덩어리": n}, ["같은 덩어리"] * n

    first_open = [next((stem(w) for w, c in t if c == "OPEN"), None) for t in toks]
    fo = [x for x in first_open if x]
    if choice(fo) and len(set(fo)) <= 4:
        A = sorted(set(fo))
        return "대비형", "갈아 끼워지는 낱말: " + " / ".join(A), " / ".join(A), dict(Counter(fo)), first_open

    tally = Counter(x for k in keys for x in set(k))
    major = [x for x, v in tally.items() if v / n >= 0.5]
    if major:
        core = " ".join(x for x in keys[0] if x in major) or " ".join(major)
        return "패턴형", "고정부 " + core + " (일부 문장은 괄호가 다르게 쳐짐)", core, {"같은 덩어리": sum(1 for k in keys if set(major) <= set(k))}, ["같은 덩어리" if set(major) <= set(k) else None for k in keys]

    return "해당없음", "고정부도 선택지도 없음", "", {}, [None] * n

# 규칙으로는 못 잡는 괄호 오류 — 학습 대상이 아닌 곳에 괄호가 쳐져 있다
FLAG_NOTES = {
    "10036": "학습 대상(불규칙 복수 teeth · mice)이 괄호 밖이고 괄호는 [These are]에 쳐져 있다",
}

def spare(labels, used):
    return next((i for i in range(len(labels)) if i not in used), 0)

def plan(typ, labels, opens):
    """①②③ 에 쓸 문장(독립 문장 번호, 0 = S1). 유형마다 고르는 기준이 다르다.
    ① 짚기  패턴형: 같은 덩어리 문장 2개(S1 제외) — 같은 말이 반복되는 걸 본다
            변화형: 같은 꼴이면서 낱말이 서로 다른 2개 — 낱말은 달라도 같은 변화
            대비형: 가장 많이 쓰인 두 쪽에서 하나씩 — 무엇이 다른지
            자리형: 부사가 서로 다른 2개 — 부사는 달라도 같은 자리
    ② 적용  패턴형: S1(학습 문장)에 패턴 쓰기 / 그 밖: ① 에 안 쓴 문장 2개(대비형은 두 쪽에서 하나씩)
    ③ 배열  패턴형은 S1(쓴 문장을 통째로 세운다), 그 밖은 ①② 에 안 쓴 문장 — 없으면 S1
    고를 수 없으면 None — 그 유닛은 문장을 더 저작해야 문제가 된다"""
    idx = [i for i, l in enumerate(labels) if l]
    if typ == "패턴형":
        rest = [i for i in idx if i != 0]
        return dict(find=rest[:2], apply=[0], arrange=0) if len(rest) >= 2 else None
    if typ in ("변화형", "자리형"):
        find, seen = [], set()
        for i in idx:
            k = opens[i] if typ == "변화형" else labels[i]
            if k not in seen: find.append(i); seen.add(k)
            if len(find) == 2: break
        rest = [i for i in idx if i not in find]
        if len(find) < 2 or len(rest) < 2: return None
        return dict(find=find, apply=rest[:2], arrange=spare(labels, find + rest[:2]))
    if typ == "대비형":
        top = [k for k, _ in Counter(l for l in labels if l).most_common(2)]
        if len(top) < 2: return None
        a = [i for i in idx if labels[i] == top[0]]; b = [i for i in idx if labels[i] == top[1]]
        if len(a) < 2 or len(b) < 2: return None
        return dict(find=[a[0], b[0]], apply=[a[1], b[1]], arrange=spare(labels, [a[0], b[0], a[1], b[1]]))
    return None

def bracket_flags(uid, indep):
    """괄호가 학습 대상을 제대로 덮는가 — 데이터를 고쳐야 하는 유닛만 표시한다"""
    out = []
    if any(not key_of(tokens(e)) for _, e, _ in indep):
        out.append("괄호 확인: 대명사만 괄호친 문장이 있다")
    if uid in FLAG_NOTES:
        out.append("괄호 확인: " + FLAG_NOTES[uid])
    return out

SLOT_FORMS = [("-ing", "~ing"), ("_ing", "~ing"), ("과거분사", "과거분사"), ("과거형", "과거형"), ("과거완료", "과거완료"),
              ("동사원형", "동사원형"), ("원형", "원형"), ("복수", "복수"), ("단수", "단수"), ("서수", "서수"), ("_er", "-er"), ("_est", "-est")]

def slot_form(indep, form):
    """패턴형인데 카드 초록이 슬롯의 꼴을 정해 둔 경우(look forward to ~ing) — 괄호는 맞고 슬롯 조건만 따로 있다"""
    if not FORM_HINT.search(form): return ""
    if sum(1 for _, e, _ in indep if form_classes(tokens(e))) / len(indep) >= 0.5: return ""
    return next((label for key, label in SLOT_FORMS if key in form), "")

def main():
    if not SRC.exists(): die(f"CSV 없음: {SRC} (UNITS_CSV로 지정)")
    rows = list(csv.reader(open(SRC, encoding="utf-8")))
    head = rows[0]
    col = {name: head.index(name) for name in ("id", "trigger", "카드 초록 (형태)", "sentence", "translation", "태그", "카드 회색 1행 (뜻)", "카드 회색 2행 (설명)")}
    units = OrderedDict(); cur = None
    for r in rows[1:]:
        if r[col["id"]].strip():
            cur = r[col["id"]].strip()
            units[cur] = dict(id=cur, trigger=r[col["trigger"]], form=r[col["카드 초록 (형태)"]],
                              mean=r[col["카드 회색 1행 (뜻)"]], desc=r[col["카드 회색 2행 (설명)"]], sents=[])
        if cur and r[col["sentence"]].strip():
            units[cur]["sents"].append((r[col["태그"]].strip(), r[col["sentence"]].strip(), r[col["translation"]].strip()))
    out = []
    for u in units.values():
        indep = [s for s in u["sents"] if not s[0].startswith("문장1-")]
        typ, why, core, sides, labels = classify(indep, u["form"])
        opens = [tuple(sorted(stem(w) for w, c in tokens(e) if c == "OPEN")) for _, e, _ in indep]
        auto = typ
        flags = bracket_flags(u["id"], indep)
        slot = slot_form(indep, u["form"]) if typ == "패턴형" else ""
        if u["id"] in OVERRIDES:
            typ, why = OVERRIDES[u["id"]]
            sides = {"사람이 분류": len(indep)} if typ != "해당없음" else {}
            labels = [None] * len(indep)
        pl = plan(typ, labels, opens)
        out.append(dict(id=u["id"], type=typ, auto=auto, manual=u["id"] in OVERRIDES, why=why, core=core, flags=flags, slot=slot, sides=sides, labels=labels, plan=pl, indep=[i for i, s in enumerate(u["sents"]) if not s[0].startswith("문장1-")], trigger=u["trigger"], form=u["form"],
                        mean=u["mean"], desc=u["desc"], sents=[[t, e, k] for t, e, k in u["sents"]]))
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    c = Counter(x["type"] for x in out)
    print(f"{len(out)}유닛 → {OUT.name}:", ", ".join(f"{k} {v}" for k, v in c.most_common()))
    short = Counter(x["type"] for x in out if not x["plan"])
    print("문장이 모자라 문제를 다 만들 수 없는 유닛:", ", ".join(f"{k} {v}" for k, v in short.most_common()))

if __name__ == "__main__":
    main()
