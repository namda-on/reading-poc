"""두 학습 흐름이 유닛마다 어떤 문장의 어느 낱말을 쓰는지 미리 정해 public/units/flow-units.gen.json 으로 굽는다.
organize_units.py 가 판정을 마친 뒤 부른다(`write`). 화면(vocab-expression-flows.html)은 이 계획을 그대로 따른다.

  패턴화 가능 → 패턴 흐름  ① 찾기(두 문장의 고정어) ② 고정어 릴레이(S1·주어 변형) ③ 문장 완성 ④ 내 말로
  패턴화 불가 → 규칙 흐름  ① 따라 만들기(S1) ② 먼저 결정 ③ 틀린 문장 고치기 ④ 정리
규칙 흐름 ②③④의 모양은 불가 이유가 정한다 — 형태(원형 → 꼴) · 자리(부사 자리) · 어순(덩어리 순서) · 일치(is / are) · 그 밖.

데이터 개선 제안 중 이 단계가 대신 만드는 것:
  - 형태 규칙의 원형·규칙 태그 — 낱말 끝을 깎고 사전(/usr/share/dict/words)으로 확인한다. 틀린 것은 BASE_FIX 에 적는다.
  - 형태·일치의 틀린 문장 — 규칙을 잘못 적용한 꼴(cryed · bigest · sended)이나, 그 자리에 오면 확실히 틀린 원형(I'm write)이다.
  - 자리·어순의 틀린 문장 — 규칙으로는 '확실히 틀린' 문장을 못 만들어(always can · had renewed it 은 맞는 문장이다) HAND_WRONG 에 손으로 적었다.
"""
import json, re
from collections import Counter

import classify_units as cu

VARIANT = ("문장1-2", "문장1-3")
DICT = set()
try:
    DICT = {w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8")}
except OSError:
    pass

# 자동 원형이 틀린 낱말 — 낱말 → (원형, 태그)
BASE_FIX = {
    "upheld": ("uphold", "불규칙"),
    "practicing": ("practice", "e 빼고 +ing"),
}

# 자리·어순의 ③ 틀린 문장 — 대괄호 문장 → 틀린 문장. 규칙으로 만들면 맞는 문장이 나오는 경우가 있어 손으로 골랐다
HAND_WRONG = {
    "[They've been working] on this project for months.": "They've been work on this project for months.",
    "We learned it [very easily].": "We learned it easily very.",
    "You [play well].": "You well play.",
    "She [studies hard].": "She hard studies.",
    "It's a [pretty good] movie.": "It's a good pretty movie.",
    "[Are they always] this quiet?": "Are always they this quiet?",
    "She [never listens].": "She listens never.",
    "[Put it down]!": "Put down it!",
    "[She can never] sit still.": "She can sit never still.",
    "There's [something strange] going on.": "There's strange something going on.",
    "[He asked me] a question.": "He asked a question me.",
    "I [found it] pretty easy.": "I found pretty easy it.",
    "I [heard them fighting].": "I heard fighting them.",
    "My mom [made me] clean my room.": "My mom made clean me my room.",
    "We [watched them] play all afternoon.": "We watched play them all afternoon.",
    "You should really [get that fixed].": "You should really get fixed that.",
    "That was [the year] my sister graduated.": "That was my sister graduated the year.",
    "There's the cafe [Emma recommended].": "There's the cafe recommended Emma.",
}

INTENS = {"very", "really", "pretty", "so", "too", "quite"}
FREQ = {"always", "usually", "often", "sometimes", "never", "rarely", "seldom", "ever"}
MANNER = {"well", "fast", "early", "late", "hard", "carefully", "quickly", "slowly", "easily", "loudly", "quietly"}
THING = {"something", "nothing", "anything", "everything", "someone", "anyone", "everyone", "no one", "somewhere", "anywhere", "nowhere", "somebody", "nobody"}
PRON_OBJ = {"me", "you", "him", "her", "it", "us", "them"}
ORD = {"first": "one", "second": "two", "third": "three", "fourth": "four", "fifth": "five", "sixth": "six", "seventh": "seven",
       "eighth": "eight", "ninth": "nine", "tenth": "ten", "eleventh": "eleven", "twelfth": "twelve", "thirteenth": "thirteen",
       "fourteenth": "fourteen", "fifteenth": "fifteen", "twentieth": "twenty", "thirtieth": "thirty"}
AGREE = {"is": "are", "are": "is", "am": "is", "was": "were", "were": "was", "do": "does", "does": "do", "have": "has", "has": "have"}
IRR_MORE = {"more": "much", "most": "much", "less": "little", "least": "little"}
NOT_ING = {"morning", "evening", "during", "building", "ceiling", "nothing", "something", "anything", "everything"}
TAG_ORDER = ["+ed", "+d", "y → ied", "자음 겹치고 +ed", "+ing", "e 빼고 +ing", "자음 겹치고 +ing", "ie → ying",
             "+est", "+st", "y → iest", "자음 겹치고 +est", "+er", "+r", "y → ier", "자음 겹치고 +er", "+'s", "+th", "불규칙"]


def tokenize(en):
    """`I'll [talk to] my parents.` → ([[I'll,0], [talk,1], [to,1], [my,0], [parents,0]], '.')
    낱말 일부만 괄호인 경우(open[ed])도 괄호로 본다. 끝의 종결부호는 따로 뗀다."""
    plain, inb, on = "", [], False
    for ch in en:
        if ch == "[": on = True; continue
        if ch == "]": on = False; continue
        plain += ch; inb.append(on)
    out = []
    for m in re.finditer(r"\S+", plain):
        a, b = m.span()
        out.append([m.group(), int(any(inb[a:b]))])
    p = ""
    if out:
        mm = re.match(r"^(.*?)([.?!]+)$", out[-1][0])
        if mm and mm.group(1): out[-1][0], p = mm.group(1), mm.group(2)
        elif mm: p = out.pop()[0]
    return out, p


def low(w): return w.lower().replace("’", "'")
def bare(w): return re.sub(r"[^a-z'\-]", "", low(w))
def cvc(s): return len(s) >= 3 and s[-1] not in "aeiouwxy" and s[-2] in "aeiou" and s[-3] not in "aeiou"
def e_base(s, short=False):
    """끝의 e 가 빠진 줄기인가 — writ·com·nic 은 e 를 되살리고, visit·open 은 그대로 둔다(사전에 visite 가 있어도).
    사전에 없는 줄기가 c·v·u 로 끝나면(practic · argu) e 가 빠진 것이다. short 는 -ed 의 us → use 처럼 두 글자 줄기를 허용한다"""
    if s not in DICT and s + "e" not in DICT: return s[-1:] in ("c", "v", "u")
    return s + "e" in DICT and (s not in DICT or (len(s) <= 4 and cvc(s)) or (short and len(s) <= 2))
def same_case(src, w): return w[:1].upper() + w[1:] if src[:1].isupper() else w


def category(form):
    if "서수" in form: return "ord"
    if "숫자" in form: return "num"
    if "과거분사" in form and "현재분사" not in form: return "pp"
    if "-ing" in form or "ing" in form or "현재분사" in form: return "ing"
    if "'s" in form or "’s" in form: return "poss"
    if "est" in form: return "sup"
    if "er" in form: return "cmp"
    return "past"


def lemma(w, cat):
    """꼴 낱말 → (원형, 규칙 태그)"""
    lw = bare(w)
    if lw in BASE_FIX: return BASE_FIX[lw]
    if cat == "poss": return re.sub(r"['’]s$", "", w), "+'s"
    if cat == "ord":
        head, _, last = lw.rpartition("-")
        if last in ORD: return (head + "-" if head else "") + ORD[last], ("+th" if ORD[last] + "th" == last else "불규칙")
        if last.endswith("th"): return (head + "-" if head else "") + last[:-2], "+th"
        return lw, "+th"
    if cat == "num": return lw.replace("-", " "), "단위는 단수"
    if lw in cu.IRR: return cu.IRR[lw], "불규칙"
    if lw in cu.IRR_CMP: return cu.IRR_CMP[lw], "불규칙"
    if lw in IRR_MORE: return IRR_MORE[lw], "불규칙"
    if lw.endswith("ing") and cat == "ing":
        s = lw[:-3]
        if s.endswith("y") and s[:-1] + "ie" in {"lie", "die", "tie"}: return s[:-1] + "ie", "ie → ying"
        if len(s) > 2 and s[-1] == s[-2] and s[-1] not in "lsz" and s[:-1] in DICT: return s[:-1], "자음 겹치고 +ing"
        if e_base(s): return s + "e", "e 빼고 +ing"
        return s, "+ing"
    for suf, y, e in (("est", "y → iest", "+st"), ("er", "y → ier", "+r")):
        if cat in ("sup", "cmp") and lw.endswith(suf):
            s = lw[:-len(suf)]
            if s.endswith("i"): return s[:-1] + "y", y
            if len(s) > 2 and s[-1] == s[-2] and s[-1] not in "lsz" and s[:-1] in DICT: return s[:-1], f"자음 겹치고 +{suf}"
            if e_base(s): return s + "e", e
            return s, "+" + suf
    if lw.endswith("ied"): return lw[:-3] + "y", "y → ied"
    if lw.endswith("ed"):
        s = lw[:-2]
        if len(s) > 2 and s[-1] == s[-2] and s[-1] not in "lsz" and s[:-1] in DICT: return s[:-1], "자음 겹치고 +ed"
        if e_base(s, short=True): return lw[:-1], "+d"
        return s, "+ed"
    return lw, "불규칙"


def is_form_word(w, cat):
    lw = bare(w)
    if not lw: return False
    if cat == "poss": return bool(re.search(r"['’]s$", w))
    if cat == "ord": return lw in ORD or bool(re.search(r"\d+(st|nd|rd|th)$", lw))
    if cat == "num": return "-" in lw
    if cat == "ing": return lw.endswith("ing") and re.search(r"[aeiouy]", lw[:-3]) and lw not in NOT_ING
    if cat == "sup": return lw.endswith("est") or lw in ("best", "worst", "most", "least")
    if cat == "cmp": return lw.endswith("er") or lw in ("better", "worse", "more", "less")
    return lw.endswith("ed") or lw in cu.IRR or lw in BASE_FIX


def naive(base, cat):
    """규칙을 그대로 붙인 꼴 — 실제 꼴과 다르면 확실히 틀린 말이다(cryed · bigest · losed · writeing)"""
    suf = {"past": "ed", "pp": "ed", "ing": "ing", "sup": "est", "cmp": "er"}.get(cat)
    if not suf: return None
    if base.endswith("e") and suf[0] == "e": return base + suf[1:]
    return base + suf


def form_wrong(word, base, tag, cat, has_next):
    """③ 틀린 꼴 — (틀린 낱말, 우선순위, 왜 확실히 틀린가). 우선순위가 낮을수록 ③ 에 먼저 쓴다"""
    lw = bare(word)
    if lw in IRR_MORE: return None, 9, ""
    n = naive(base, cat) if " " not in base else None
    if n and n != lw and tag not in ("+ed", "+ing", "+est", "+er"):
        return n, (0 if tag == "불규칙" else 1 if "→" in tag else 2 if "겹치고" in tag else 2.5), "규칙을 잘못 붙인 꼴"
    if cat in ("ing", "pp", "cmp") and base != lw: return base, 3, "그 자리에 올 수 없는 원형"
    if cat == "poss" and has_next and base != lw: return base, 3, "명사 앞에서 's 가 빠진 꼴"
    if cat == "pp" and n and n != lw: return n, 2, "규칙을 잘못 붙인 꼴"
    if cat == "ord" and base != lw: return base, 3, "서수 자리에 쓴 기수"
    if cat == "num": return lw + "s", 3, "단위에 s 를 붙인 꼴"
    return None, 9, ""


def anchor_marks(form, sents, anc, keys_of):
    """문장마다 고정어 낱말에 고정어 키를 단다. 괄호 안을 먼저 찾고, 없으면 문장 전체에서 찾는다"""
    form_keys = keys_of(" ".join(re.findall(r"[A-Za-z']+", form)))
    family = {c: {k for k, cc in form_keys if cc == c} for c in ("BE", "DO", "HAVE")}
    fam = lambda c: c in family and len(family[c]) == 1
    def hit(word, k, c):
        ks = keys_of(word)
        return any(cc == c for _, cc in ks) if fam(c) else any(kk == k for kk, _ in ks)
    marks = []
    for toks in sents:
        m = [None] * len(toks)
        for k, c in anc:
            # 한 낱말이 고정어 둘을 품을 수 있다(I'm = I + am) — 이미 표시된 낱말도 다시 맞춰 본다
            idx = [i for i, (w, b) in enumerate(toks) if b and hit(w, k, c)] or [i for i, (w, b) in enumerate(toks) if hit(w, k, c)]
            if idx and m[idx[0]] is None: m[idx[0]] = k
        marks.append(m)
    return marks, [{"k": k, "c": c, "fam": fam(c)} for k, c in anc]


def diff_region(a, b):
    """두 낱말 목록에서 달라진 구간 — (a 시작, a 끝, b 시작, b 끝)"""
    la, lb = [low(w) for w in a], [low(w) for w in b]
    i = 0
    while i < min(len(la), len(lb)) and la[i] == lb[i]: i += 1
    j = 0
    while j < min(len(la), len(lb)) - i and la[-1 - j] == lb[-1 - j]: j += 1
    return i, len(la) - j, i, len(lb) - j


def fix_plan(i, toks, p, wrong_words, src, why):
    """③ — 틀린 문장, 틀린 구간(wr), 맞는 구간(cr), 고치는 방법. 같은 낱말 하나가 여러 자리에서 바뀌었으면(bader and bader)
    한 번 쳐서 모두 고친다(mode type, pos)"""
    words = [w for w, _ in toks]
    if len(words) == len(wrong_words):
        pos = [k for k, (a, b) in enumerate(zip(wrong_words, words)) if low(a) != low(b)]
        if pos and len({low(words[k]) for k in pos}) == 1 and len({low(wrong_words[k]) for k in pos}) == 1:
            return {"i": i, "wrong": wrong_words, "wr": [pos[0], pos[-1] + 1], "cr": [pos[0], pos[-1] + 1], "pos": pos, "mode": "type", "src": src, "why": why}
    a0, a1, b0, b1 = diff_region(wrong_words, words)
    if a0 >= a1 or b0 >= b1: return None
    mode = "arrange" if sorted(map(low, wrong_words[a0:a1])) == sorted(map(low, words[b0:b1])) else ("type" if b1 - b0 == 1 and a1 - a0 == 1 else "arrange")
    return {"i": i, "wrong": wrong_words, "wr": [a0, a1], "cr": [b0, b1], "mode": mode, "src": src, "why": why}


def plan_pattern(r, S, keys_of, anchors):
    sents = [(t, e, k) for t, e, k, _ in r["sents"]]
    anc = anchors(r["form"], sents)
    marks, akeys = anchor_marks(r["form"], [s["t"] for s in S], anc, keys_of)
    for s, m in zip(S, marks):
        for tok, k in zip(s["t"], m): tok.append(k or 0)
    has = lambda i: any(tok[2] for tok in S[i]["t"])
    keyset = lambda i: {tok[2] for tok in S[i]["t"] if tok[2]}
    indep = [i for i, s in enumerate(S) if s["tag"] not in VARIANT]
    var = [i for i, s in enumerate(S) if s["tag"] in VARIANT]
    cand = sorted([i for i in indep if i and has(i)], key=lambda i: (S[i]["tag"] == "어려운", keyset(i) != keyset(0), len(S[i]["t"])))
    find = cand[:2]
    if len(find) < 2: find += [i for i in var if has(i) and i not in find][:2 - len(find)]
    relay = [0] + [i for i in var if has(i)]
    if len(relay) < 3: relay += [i for i in indep if i not in find and i not in relay and has(i)][:3 - len(relay)]
    build = next((i for i in indep if i not in find and i not in relay and has(i)), find[-1] if find else 0)
    return {"find": find, "relay": relay, "build": build, "anc": akeys}


def plan_rule(r, S, kind, traps):
    indep = [i for i, s in enumerate(S) if s["tag"] not in VARIANT]
    var = [i for i, s in enumerate(S) if s["tag"] in VARIANT]
    rest = [i for i in indep if i] + var
    plan = {"follow": 0, "decide": None, "fix": None, "sort": None}
    if kind == "form":
        cat = category(r["form"])
        info = {}
        for i, s in enumerate(S):
            t = s["t"]
            # 괄호 안을 먼저 찾고, 없으면 괄호 밖에서 찾는다([I'm] partying [tomorrow] 의 partying)
            ws = [(j, w) for j, (w, bb) in enumerate(t) if bb and is_form_word(w, cat)] or [(j, w) for j, (w, bb) in enumerate(t) if is_form_word(w, cat)]
            if not ws: continue
            j, w = ws[0] if cat == "cmp" else ws[-1]
            run = []  # j 가 든 괄호 덩어리에서 j 뒤의 낱말
            k = j + 1
            while k < len(t) and t[k][1]: run.append(bare(t[k][0])); k += 1
            adj = next((x for x in run if x not in ("and", "more", "most", "than")), "")
            if bare(w) in ("more", "most") and adj:
                # more / most + 형용사 — 꼴이 바뀌는 낱말이 아니라 앞에 낱말을 더하는 규칙이라 ②③ 에는 쓰지 않는다
                info[i] = {"ti": j, "w": f"{bare(w)} {adj}", "base": adj, "tag": f"{bare(w)} + 형용사", "wrong": None, "pri": 9, "why": "", "peri": 1}
                continue
            base, tag = lemma(w, cat)
            wrong, pri, why = form_wrong(w, base, tag, cat, j + 1 < len(t))
            info[i] = {"ti": j, "w": w, "base": base, "tag": tag, "wrong": wrong, "pri": pri, "why": why}
        plan["cat"] = cat
        plan["info"] = {str(i): v for i, v in info.items()}
        base0 = info.get(0, {}).get("base")
        dec = sorted([i for i in rest if i in info and not info[i].get("peri")], key=lambda i: (i in var, info[i]["base"] == base0, S[i]["tag"] == "어려운"))
        fixc = sorted([i for i in rest if i in info and info[i]["wrong"]], key=lambda i: (i in var, info[i]["pri"]))
        d = dec[0] if dec else None
        f = next((i for i in fixc if i != d), None)
        if f is None and fixc and len(dec) > 1:  # ③ 에 쓸 문장이 ② 와 겹치면 ② 를 다른 문장으로
            f = fixc[0]; d = next((i for i in dec if i != f), None)
        if d is not None:
            plan["decide"] = {"i": d, "ti": info[d]["ti"], "base": info[d]["base"], "tag": info[d]["tag"]}
        hand = next((i for i in rest if S[i]["en"] in HAND_WRONG), None)
        if hand is not None:
            if hand == d: d = next((i for i in dec if i != hand), None)
            wt, _ = tokenize(HAND_WRONG[S[hand]["en"]])
            plan["decide"] = d is not None and {"i": d, "ti": info[d]["ti"], "base": info[d]["base"], "tag": info[d]["tag"]} or None
            plan["fix"] = fix_plan(hand, S[hand]["t"], S[hand]["p"], [w for w, _ in wt], "hand", "")
        elif f is not None:
            v, s = info[f], S[f]
            # 같은 낱말이 되풀이되는 꼴(worse and worse)은 둘 다 바꾼다
            wrong = [same_case(w, re.sub(re.escape(bare(v["w"])), v["wrong"], low(w))) if bare(w) == bare(v["w"]) else w for w, _ in s["t"]]
            plan["fix"] = fix_plan(f, s["t"], s["p"], wrong, "auto", v["why"])
        items, seen = [], set()
        for i in indep + var:
            v = info.get(i)
            if v and bare(v["w"]) not in seen:
                seen.add(bare(v["w"])); items.append({"w": v["w"] if v.get("peri") else bare(v["w"]), "base": v["base"], "tag": v["tag"]})
        tags = sorted({x["tag"] for x in items}, key=lambda t: TAG_ORDER.index(t) if t in TAG_ORDER else 50)
        plan["sort"] = {"bins": tags, "items": items}
    elif kind == "agree":
        def aux(i):
            return next(((j, w) for j, (w, b) in enumerate(S[i]["t"]) if b and low(w) in AGREE), None)
        cands = [i for i in rest if aux(i)]
        d = cands[0] if cands else None
        f = next((i for i in cands if i != d), None)
        if d is not None:
            j, w = aux(d)
            plan["decide"] = {"i": d, "ti": j, "opts": [w, same_case(w, AGREE[low(w)])]}
        if f is not None:
            j, w = aux(f)
            words = [x for x, _ in S[f]["t"]]
            plan["fix"] = fix_plan(f, S[f]["t"], S[f]["p"], words[:j] + [same_case(w, AGREE[low(w)])] + words[j + 1:], "auto", "주어와 맞지 않는 꼴")
    else:
        hand = next((i for i in rest if S[i]["en"] in HAND_WRONG), None)
        if hand is not None:
            wt, _ = tokenize(HAND_WRONG[S[hand]["en"]])
            plan["fix"] = fix_plan(hand, S[hand]["t"], S[hand]["p"], [w for w, _ in wt], "hand", "")
        elif kind == "other":
            for i in rest:
                tr = traps.get(S[i]["en"])
                if not tr: continue
                k = iter(tr[0])
                wrong_en = re.sub(r"\[([^\]]+)\]", lambda m: m.group(1) if (v := next(k, "-")) == "-" else v, S[i]["en"])
                wt, _ = tokenize(wrong_en)
                plan["fix"] = fix_plan(i, S[i]["t"], S[i]["p"], [w for w, _ in wt], "trap", ""); break
        used = {plan["fix"]["i"]} if plan["fix"] else set()
        d = next((i for i in rest if i not in used), None)
        if kind == "place" and d is not None:
            ws = S[d]["t"]
            def movable(i):
                t = S[i]["t"]
                br = [(j, low(w).strip(",")) for j, (w, b) in enumerate(t) if b]
                if r["id"] == "10132": return next((j for j, w in br if w in PRON_OBJ), None)
                if r["id"] == "10365": return next((j for j, w in br if w not in THING), None)
                for group in (INTENS, FREQ, MANNER):
                    j = next((j for j, w in br if w in group), None)
                    if j is not None: return j
                return next((j for j, w in br if w.endswith("ly")), None)
            d = next((i for i in rest if i not in used and movable(i) is not None), None)
            if d is not None: plan["decide"] = {"i": d, "mi": movable(d)}
        elif d is not None:
            # 괄호 밖은 이어진 덩어리 하나로, 괄호 안은 낱말 하나씩 — 결정이 괄호 안 순서에 모이게 한다
            chunks, cur = [], None
            for j, (w, b) in enumerate(S[d]["t"]):
                if b: chunks.append([j, j + 1]); cur = None
                elif cur is not None: cur[1] = j + 1
                else: cur = [j, j + 1]; chunks.append(cur)
            plan["decide"] = {"i": d, "chunks": chunks}
    return plan


KIND = [("형태 규칙", "form"), ("자리 규칙", "place"), ("어순 규칙", "order"), ("일치 규칙", "agree")]


def write(recs, path, keys_of, anchors, traps_path):
    traps = json.load(open(traps_path, encoding="utf-8")) if traps_path.exists() else {}
    out, cnt = [], Counter()
    for r in recs:
        S = []
        for tag, en, kr, new in r["sents"]:
            t, p = tokenize(en)
            S.append({"tag": tag, "en": en, "kr": kr, "nw": int(bool(new)), "t": t, "p": p})
        uid = r["new"] or r["orig"]
        u = {"id": uid, "orig": r["orig"], "form": r["form"], "mean": r["mean"], "desc": r.get("desc", ""), "typ": r["typ"],
             "pat": r["pat"], "anc": r["anc"], "why": r["why"], "chk": r["chk"], "s": S}
        if r["pat"] == "가능":
            u["kind"] = "pattern"
            u["plan"] = plan_pattern(r, S, keys_of, anchors)
        else:
            kind = next((k for pre, k in KIND if r["why"].startswith(pre)), "other")
            if uid == "10328": kind = "other"  # 분리형 구동사 — 목적어가 명사면 두 자리가 다 맞아 자리 하나를 고르는 과제가 안 된다
            u["kind"] = kind
            u["plan"] = plan_rule(dict(r, id=uid), S, kind, traps)
        cnt[u["kind"]] += 1
        out.append(u)
    lex = {k: sorted(getattr(cu, k)) for k in ("PERS", "BE", "DO", "HAVE", "MODAL", "NEG", "FUNC", "IS_HOST")}
    lex.update(CONTR=cu.CONTR, IRR=cu.IRR, IRR_CMP=cu.IRR_CMP)
    json.dump({"lex": lex, "units": out}, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    rule = [u for u in out if u["kind"] != "pattern"]
    print(f"흐름 계획: {len(out)}유닛 — " + " · ".join(f"{k} {v}" for k, v in cnt.items())
          + f" · 규칙 흐름 ③ 있음 {sum(1 for u in rule if u['plan']['fix'])}/{len(rule)}")
