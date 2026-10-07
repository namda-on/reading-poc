#!/usr/bin/env python3
"""공통 학습 방식(비교 → 쓰기) 문항을 만든다 — 구조형·해당없음을 뺀 네 유형.

입력: public/vocab-expression-units.gen.json (scripts/classify_units.py 산출물)
사전: DICT_WORDS, 기본 /usr/share/dict/words — 원형을 되살릴 때 후보가 실제 낱말인지 가린다
산출: public/vocab-expression-compare.gen.json

네 유형에 공통인 과제는 '맞는 문장과 흔히 틀리는 문장을 나란히 놓고 고르기'다.
유형마다 다른 것은 비교 상대 하나뿐이고, 그 상대는 그 유형이 틀리는 방식 그대로다.
  - 패턴형: 굳은 표현의 낱말 하나를 헷갈리는 짝으로 바꾼다 (get up → get on, If I were → If I was)
  - 변화형: 바뀐 낱말을 원형으로 되돌린다 (talked → talk, smallest → small)
  - 대비형: 다른 후보를 고른다 (to buy → buying, at → on)
  - 자리형: 부사를 다른 자리로 옮긴다 (is always → always is)
"""
import json, os, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_units import IRR, ORD, tokens, stem, form_classes, POS_ADV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "vocab-expression-units.gen.json"
OUT = ROOT / "public" / "vocab-expression-compare.gen.json"
DICT = Path(os.environ.get("DICT_WORDS", "/usr/share/dict/words"))

def die(msg):
    print("error:", msg, file=sys.stderr); sys.exit(1)

if not DICT.exists(): die(f"사전 없음: {DICT} (DICT_WORDS로 지정)")
WORDS = {w.strip().lower() for w in open(DICT, encoding="utf-8", errors="ignore")}
PAST = {v: k for k, v in IRR.items() if k not in ("read",)}   # go → went 처럼 원형 → 과거형(마지막에 등록된 것)
for base, past in (("go", "went"), ("get", "got"), ("see", "saw"), ("give", "gave"), ("take", "took"), ("make", "made"),
                   ("come", "came"), ("become", "became"), ("find", "found"), ("feel", "felt"), ("keep", "kept"), ("have", "had")):
    PAST[base] = past
ORD_TO_CARD = {"first": "one", "second": "two", "third": "three", "fourth": "four", "fifth": "five", "sixth": "six",
               "seventh": "seven", "eighth": "eight", "ninth": "nine", "tenth": "ten", "twelfth": "twelve",
               "fifteenth": "fifteen", "twentieth": "twenty"}
VOWELS = set("aeiou")

SHORT = {"doing": "do", "going": "go", "being": "be", "seeing": "see", "using": "use", "used": "use", "dying": "die",
         "lying": "lie", "tying": "tie", "saying": "say", "paying": "pay", "playing": "play", "staying": "stay"}
# 과거분사 — 원래 낱말이 과거분사면 바꾼 동사도 과거분사로(haven't given → haven't taken, took 가 아니라)
PP = {"give": "given", "take": "taken", "do": "done", "go": "gone", "see": "seen", "make": "made", "get": "gotten",
      "have": "had", "come": "come", "bring": "brought", "keep": "kept", "say": "said", "tell": "told", "put": "put",
      "set": "set", "let": "let", "hear": "heard", "find": "found", "pay": "paid", "gain": "gained", "look": "looked"}
PP_FORMS = {"given", "taken", "done", "gone", "seen", "gotten", "written", "eaten", "broken", "known", "shown", "stolen",
            "bitten", "fallen", "forgotten", "driven", "spoken", "chosen", "worn", "thrown", "drawn", "grown", "frozen", "hidden"}

def cvc(w):
    return len(w) >= 3 and w[-1] not in VOWELS | set("wxy") and w[-2] in VOWELS and w[-3] not in VOWELS

def is_word(w): return w in WORDS

def base_of(w):
    """활용형 → 원형. 사전에 있는 후보를 고르되, 자음-모음-자음으로 끝나면 e 를 붙인 쪽을 먼저 본다(hoped → hope, opened → open)"""
    w = w.lower()
    if w in SHORT: return SHORT[w]
    if w in IRR: return IRR[w]
    if w in ("better", "best"): return "good"
    if w in ("worse", "worst"): return "bad"
    for suf in ("ing", "ed", "est", "er"):
        if not w.endswith(suf) or len(w) <= len(suf) + 1: continue
        b = w[:-len(suf)]
        cands = []
        if b.endswith("i") and suf != "ing": cands.append(b[:-1] + "y")           # cried, happiest, prettier
        if len(b) >= 2 and b[-1] == b[-2] and b[-1] not in "ls": cands.append(b[:-1])  # stopped, biggest
        if cvc(b) or len(b) <= 2: cands += [b + "e", b]
        else: cands += [b, b + "e"]
        if suf == "ed" and not w.endswith("eed"): cands.append(w[:-1])             # used → use
        for c in cands:
            if is_word(c): return c
    return None

def ing_of(b):
    if b.endswith("ie"): return b[:-2] + "ying"
    if b.endswith("e") and not b.endswith("ee"): return b[:-1] + "ing"
    if cvc(b) and sum(ch in VOWELS for ch in b) == 1: return b + b[-1] + "ing"
    return b + "ing"

def ed_of(b):
    if b in PAST: return PAST[b]
    if b.endswith("e"): return b + "d"
    if b.endswith("y") and b[-2] not in VOWELS: return b[:-1] + "ied"
    if cvc(b) and sum(ch in VOWELS for ch in b) == 1: return b + b[-1] + "ed"
    return b + "ed"

def s_of(b):
    if b in ("have",): return "has"
    if re.search(r"(s|sh|ch|x|z|o)$", b): return b + "es"
    if b.endswith("y") and b[-2] not in VOWELS: return b[:-1] + "ies"
    return b + "s"

def match_case(src, new):
    return new[:1].upper() + new[1:] if src[:1].isupper() else new

def plain(s): return s.replace("[", "").replace("]", "")

def replace_word(sent, old, new, inside=True):
    """대괄호 안(inside)에서 낱말 old 를 처음 한 번 new 로 바꾼다. 못 바꾸면 None"""
    def sub_part(m):
        part = m.group(1)
        nm = re.sub(r"(?i)(?<![A-Za-z'’])" + re.escape(old) + r"(?![A-Za-z'’])",
                    lambda x: match_case(x.group(0), new), part, count=1)
        return "[" + nm + "]"
    if inside:
        out = re.sub(r"\[([^\]]+)\]", sub_part, sent)
    else:
        out = re.sub(r"(?i)(?<![A-Za-z'’])" + re.escape(old) + r"(?![A-Za-z'’])", lambda x: match_case(x.group(0), new), sent, count=1)
    return out if out != sent else None

def bracket_words(sent):
    return [w for part in re.findall(r"\[([^\]]+)\]", sent) for w in re.findall(r"[A-Za-z'’\-]+", part)]

# ---------- 유형별 비교 상대 ----------

# 패턴형 — 헷갈리는 짝(같은 자리에 올 수 있는 말). 굳은 표현에서 한 낱말을 바꾸면 다른 뜻이 되거나 틀린 문장이 된다
CONFUSE = {
    "up": "on", "on": "in", "in": "on", "at": "in", "out": "up", "off": "out", "down": "up", "away": "out",
    "back": "again", "over": "on", "around": "about", "to": "for", "for": "to", "of": "for", "with": "to",
    "about": "of", "from": "of", "by": "with", "into": "in",
    "were": "was", "was": "were", "are": "is", "is": "are", "am": "is",
    "do": "does", "does": "do", "did": "do", "don't": "doesn't", "doesn't": "don't", "didn't": "don't",
    "can": "could", "could": "can", "will": "would", "would": "will", "should": "would",
    "a": "the", "the": "a", "an": "the", "some": "any", "any": "some", "much": "many", "many": "much",
}
PRIORITY = ["were", "was", "don't", "doesn't", "do", "does", "up", "out", "off", "down", "away", "back", "over", "around",
            "to", "for", "of", "with", "about", "from", "by", "on", "in", "at", "into",
            "can", "could", "will", "would", "should", "are", "is", "am", "some", "any", "much", "many", "a", "the", "an", "did", "didn't"]

# 기능어가 없는 굳은 표현(pay attention, make a mistake)에서 학습자가 실제로 헷갈리는 것은 가벼운 동사다
LIGHT = {"make": "do", "do": "make", "take": "have", "have": "take", "get": "take", "give": "take", "pay": "give",
         "gain": "get", "let": "make", "keep": "hold", "say": "tell", "tell": "say", "see": "look", "look": "see",
         "watch": "see", "hear": "listen", "come": "go", "go": "come", "bring": "take", "put": "set", "set": "put"}
CONFUSE.update({"as": "like"})
PRIORITY.append("as")

def inflect_like(base, like):
    lw = like.lower()
    if lw == base: return base
    if lw in PP_FORMS: return PP.get(base, ed_of(base))
    if lw in IRR or lw.endswith("ed"): return ed_of(base)
    if lw.endswith("ing"): return ing_of(base)
    if lw.endswith("s") and not lw.endswith("ss"): return s_of(base)
    return base

def wrong_pattern(sent):
    words = [w.lower().replace("’", "'") for w in bracket_words(sent)]
    for target in PRIORITY:
        if target in words:
            new = CONFUSE[target]
            if target == "were" and not re.search(r"(?i)\b(I|he|she|it)\s+were\b", plain(sent)): continue
            out = replace_word(sent, target, new)
            if out: return out, target, new
    for w in bracket_words(sent):
        lw = w.lower()
        base = lw if lw in LIGHT else base_of(lw)
        if base in LIGHT:
            new = inflect_like(LIGHT[base], w)
            out = replace_word(sent, w, new)
            if out: return out, w, new
    return None

def wrong_change(sent, form_cls):
    """바뀐 낱말을 원형으로 — 변화형은 '모양을 안 바꿨다'가 대표 실수다"""
    for w in bracket_words(sent):
        lw = w.lower()
        if form_cls == "N-'s" and re.search(r"['’]s$", lw):
            base = w[:-2]
        elif form_cls == "ORD" and lw in ORD_TO_CARD:
            base = ORD_TO_CARD[lw]
        elif form_cls in ("V-ed", "V-ing", "A-est", "A-er"):
            ok = {"V-ed": lw in IRR or lw.endswith("ed"), "V-ing": lw.endswith("ing"),
                  "A-est": lw.endswith("est") or lw in ("best", "worst"), "A-er": lw.endswith("er") or lw in ("better", "worse")}[form_cls]
            if not ok or len(lw) <= 3: continue
            base = base_of(lw)
            if not base or base == lw: continue
        else:
            continue
        out = replace_word(sent, w, base)
        if out: return out, w, base
    return None

def swap_form(w, to):
    """대비형 꼴 바꾸기: -ing ↔ to + 원형, -ing ↔ -ed"""
    lw = w.lower()
    b = base_of(lw)
    if not b: return None
    if to == "V-ing": return ing_of(b)
    if to == "V-ed": return ed_of(b)
    if to == "to-V": return "to " + b
    return None

def wrong_contrast(sent, label, sides):
    others = [k for k, _ in sorted(sides.items(), key=lambda kv: -kv[1]) if k != label]
    if not others: return None
    alt = others[0]
    words = bracket_words(sent)
    if label in ("V-ing", "V-ed", "to-V"):
        if label == "to-V":
            m = re.search(r"\[[^\]]*\bto\s+([A-Za-z]+)", sent)
            if not m: return None
            verb = m.group(1)
            new = swap_form(verb, alt) if alt != "to-V" else None
            if not new: new = ing_of(verb.lower()) if alt == "V-ing" else None
            if not new: return None
            out = sent.replace("to " + verb, new, 1)
            return (out, "to " + verb, new) if out != sent else None
        for w in words:
            lw = w.lower()
            if (label == "V-ing" and lw.endswith("ing")) or (label == "V-ed" and (lw.endswith("ed") or lw in IRR)):
                new = swap_form(w, alt)
                if not new: continue
                out = replace_word(sent, w, new)
                if out: return out, w, new
        return None
    # 갈아 끼워지는 낱말: 그 문장이 쓴 쪽(label)을 다른 쪽으로
    for w in words:
        lw = w.lower().replace("’", "'")
        if lw == label:
            out = replace_word(sent, w, alt)
            if out: return out, w, alt
        if stem(lw) == label or (label == "can" and lw == "can't") or (label == "could" and lw == "couldn't"):
            if lw in ("can't", "couldn't", "won't", "wouldn't"):
                new = {"can't": "couldn't", "couldn't": "can't", "won't": "wouldn't", "wouldn't": "won't"}[lw]
            else:
                # 첫 낱말이 번갈아 오는 유닛(become / get / turn) — 다른 쪽 동사를 같은 활용으로
                alt_base = base_of(alt) or alt
                if not is_word(alt_base):
                    alt_base = next((x for x in (alt + "e", alt) if is_word(x)), None)
                if not alt_base: return None
                if lw in IRR or lw.endswith("ed"): new = ed_of(alt_base)
                elif lw.endswith("ing"): new = ing_of(alt_base)
                elif lw.endswith("s") and not lw.endswith("ss"): new = s_of(alt_base)
                else: new = alt_base
            out = replace_word(sent, w, new)
            if out: return out, w, new
    return None

BE_CONTR = {"'s": "is", "'re": "are", "'m": "am"}

def wrong_position(sent):
    """부사를 다른 자리로 — be동사 뒤에 있던 것은 앞으로, 동사 앞에 있던 것은 뒤로, 형용사 앞의 정도부사는 뒤로"""
    toks = re.findall(r"\[[^\]]*\]|[^\s]+", sent)
    flat = plain(sent).split()
    low = [re.sub(r"[^a-z'’]", "", t.lower()).replace("’", "'") for t in flat]
    for i, w in enumerate(low):
        if w not in POS_ADV or w in ("so", "too", "even", "just", "also", "ever"): continue
        prev = low[i - 1] if i else ""
        out = None
        if i + 1 < len(flat) and w in ("very", "really", "pretty"):
            out = flat[:i] + [flat[i + 1].rstrip(".,!?"), flat[i]] + flat[i + 2:]
            if flat[i + 1][-1:] in ".,!?": out[i + 1] += flat[i + 1][-1]
        elif prev in ("is", "are", "was", "were", "am"):
            out = flat[:i - 1] + [flat[i], flat[i - 1]] + flat[i + 1:]
        elif any(prev.endswith(c) for c in BE_CONTR) and "'" in prev:
            head, tail = re.match(r"(.+?)('s|'re|'m)$", flat[i - 1].replace("’", "'")).groups()
            out = flat[:i - 1] + [head, flat[i], BE_CONTR[tail]] + flat[i + 1:]
        elif i + 1 < len(flat):
            j = i + 1
            if low[j] in ("can", "will", "would", "could", "should") and j + 1 < len(flat): j += 1
            if flat[j][-1:] in ".,!?": continue
            out = flat[:i] + flat[i + 1:j + 1] + [flat[i]] + flat[j + 1:]
        if out:
            if i == 0 or out[0] != flat[0]:
                out[0] = out[0][:1].upper() + out[0][1:]
                for k in range(1, len(out)):
                    if out[k] == flat[0] and flat[0] not in ("I",): out[k] = flat[0][:1].lower() + flat[0][1:]
            return " ".join(out), w, "자리"
    # 목록 밖 자리 — 대명사는 동사와 부사 사이(Pick me up → Pick up me), 두 낱말 괄호는 순서를 바꾼다(teaches well → well teaches)
    PARTICLES = {"up", "down", "on", "off", "out", "in", "away", "back", "over", "around"}
    PRONS = {"me", "you", "him", "her", "it", "us", "them"}
    for m in re.finditer(r"\[([^\]]+)\]", sent):
        ws = m.group(1).split()
        if {x.lower() for x in ws} & {"too", "so", "also"}: continue
        if len(ws) == 3 and ws[1].lower() in PRONS and ws[2].lower().strip(".,!?") in PARTICLES:
            new = " ".join([ws[0], ws[2], ws[1]])
        elif len(ws) == 2 and ws[1].lower().strip(".,!?") not in PARTICLES:
            new = " ".join([ws[1].lower(), ws[0][:1].lower() + ws[0][1:] if ws[0] != "I" else ws[0]])
            if m.start() == 0: new = new[:1].upper() + new[1:]
        else:
            continue
        out = sent[:m.start()] + new + sent[m.end():]
        return plain(out), m.group(1), "자리"
    return None

def reason(u, right_w, wrong_w):
    """고른 뒤 보여줄 한 줄 — 저작된 설명(카드 회색 2행)이 있으면 그것, 없으면 유형별 틀(영어 뒤에 조사를 붙이지 않는다)"""
    t = u["type"]
    if u["desc"]: return u["desc"]
    if t == "패턴형": return f"통째로 굳은 표현이에요 · {u['form'].strip()} ({right_w} ✓ · {wrong_w} ✗)"
    if t == "변화형": return f"{wrong_w} → {right_w} · {u['mean']}"
    if t == "대비형": return f"{right_w} ✓ · {wrong_w} ✗ · {u['mean']}"
    return f"자리가 정해져 있어요 · {right_w}"

def main():
    if not SRC.exists(): die(f"분류 결과 없음: {SRC} — scripts/classify_units.py 를 먼저 돌린다")
    units = json.loads(SRC.read_text(encoding="utf-8"))
    out, stat = [], Counter()
    for u in units:
        t = u["type"]
        if t not in ("패턴형", "변화형", "대비형", "자리형"): continue
        sents = u["sents"]; ind = u["indep"]; labels = u["labels"]
        labeled = [ind[k] for k, l in enumerate(labels) if l] or list(ind)
        variants = [i for i, s in enumerate(sents) if s[0].startswith("문장1-")]
        def label_of(i):
            return labels[ind.index(i)] if i in ind else (labels[0] if labels else None)
        def make(i):
            s = sents[i][1]
            if t == "패턴형": r = wrong_pattern(s)
            elif t == "변화형": r = wrong_change(s, label_of(i))
            elif t == "대비형": r = wrong_contrast(s, label_of(i), {k: v for k, v in u["sides"].items() if k != "사람이 분류"})
            else: r = wrong_position(s)
            if not r: return None
            wrong, a, b = r
            if plain(wrong) == plain(s): return None
            return dict(en=s, kr=sents[i][2], wrong=plain(wrong), why=reason(u, a, b))
        # ① 짚기 2 · ② 비교 2 · ③ 쓰기 2 — 대비형의 ② 는 두 쪽에서 하나씩
        pool = labeled + [i for i in variants if t == "패턴형"]
        find = pool[:2]
        rest = [i for i in pool if i not in find]
        if t == "대비형" and u["plan"]:
            cmp_idx = [ind[k] for k in u["plan"]["apply"]]
        else:
            cmp_idx = rest[:2] if len(rest) >= 2 else rest + find[:2 - len(rest)]
        compare = [c for c in (make(i) for i in cmp_idx) if c]
        if len(compare) < 2:
            extra = [i for i in pool if i not in cmp_idx]
            for i in extra:
                if len(compare) >= 2: break
                c = make(i)
                if c: compare.append(c); cmp_idx.append(i)
        write_idx = [i for i in pool if i not in find and i not in cmp_idx][:2] or find[:1]
        if len(write_idx) < 2: write_idx += [i for i in find if i not in write_idx][:2 - len(write_idx)]
        ok = len(find) == 2 and len(compare) >= 2
        stat[(t, ok)] += 1
        if not ok: continue
        out.append(dict(id=u["id"], type=t, form=u["form"], mean=u["mean"], desc=u["desc"],
                        find=[dict(en=sents[i][1], kr=sents[i][2]) for i in find],
                        compare=compare[:2],
                        write=[dict(en=sents[i][1], kr=sents[i][2]) for i in write_idx]))
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for t in ("패턴형", "변화형", "대비형", "자리형"):
        print(f"{t}: {stat[(t, True)]}/{stat[(t, True)] + stat[(t, False)]} 유닛에서 비교 문항을 만들었다")

if __name__ == "__main__":
    main()
