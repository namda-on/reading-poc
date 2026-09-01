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
슬롯(변하는 부분)은 주어진 채로 고정하고 프레임 자리를 비운다. 그래서 `form`의 리터럴
프레임이 대표문장과 응용예문 **모두에 실제로** 등장하는 그룹만 쓴다(2단어 이상).

출력: public/vocab-expression.data.json (커밋되는 생성물). 손으로 편집하지 말 것.
"""
import csv, json, os, re, sys
from collections import OrderedDict
from pathlib import Path

DL = Path.home() / "Downloads"
EXPR_CSV  = Path(os.environ.get("VE_EXPR_CSV",  DL / "유기적 통합모드 문장 (공유용) - 문장 제출(0827).csv"))
VOCAB_CSV = Path(os.environ.get("VE_VOCAB_CSV", DL / "All_(2026-09-01_20_14_12).csv"))
GSE_CSV   = Path(os.environ.get("VE_GSE_CSV",   DL / "gse_corrected_final_0624 - 보정결과_전체.csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "vocab-expression.data.json"

MAX_ITEMS = int(os.environ.get("VE_MAX_ITEMS", "60"))   # 0이면 전체
VOCAB_FILTER_SKIP = {"sexual", "unnecessary"}
BRACKET = re.compile(r"\[([^\]]+)\]")
INFL = re.compile(r"^(?:s|es|ed|d|ing|er|est|ies|ier|iest|'s|')$")
SLOT = re.compile(r"_{2,}|~")
KOR = re.compile(r"[가-힣]")
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
    """문장에서 트리거 어휘(굴절형 포함) 한 곳을 [..]로 감싼다. 못 찾으면 None."""
    best = None
    for m in re.finditer(r"[A-Za-z']+", sent):
        if m.group(0).lower() == trigger.lower():
            best = m
            break
        if best is None and infl_match(m.group(0), trigger):
            best = m
    if not best:
        return None
    return sent[:best.start()] + "[" + best.group(0) + "]" + sent[best.end():], best.group(0)


def frame_literals(form):
    """form을 슬롯 기준으로 쪼개 리터럴 프레임 조각을 순서대로 반환. 못 쓰면 None.

    `주어 + didn't + ______` 처럼 한글 자리표시자가 섞였거나 `Are / Is + ...` 처럼
    프레임 자체에 대안이 박힌 표기는 문장에 그대로 등장하지 않으므로 제외한다.
    """
    if not SLOT.search(form) or KOR.search(form) or "/" in form:
        return None
    out = []
    for part in SLOT.split(form):
        part = re.sub(r"\s+", " ", part.strip().strip("().")).strip()
        if part and not re.fullmatch(r"[.?!,]*", part):
            out.append(part)
    return out or None


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


def make_vocab_a(v, trigger):
    """버전 A: 어휘 CSV의 learnSentence. 빈칸 정답은 학습 대상 어휘와 같아야 한다."""
    m = BRACKET.search(v["ls"])
    if not m:
        return None
    ans = m.group(1).strip()
    if not infl_match(ans, trigger) and not infl_match(trigger, ans):
        return None      # 다른 단어를 괄호친 예문(baggage claim→[baggage]) 제외
    return {"answer": ans,
            "enLines": [x.strip() for x in v["ls"].split("\n")],
            "koLines": [x.strip() for x in v["lsm"].split("\n")]}


def main():
    vocab, gse, groups = load_vocab(), load_gse(), load_groups()
    items, skipped = [], {"조인실패": 0, "버전A불가": 0, "버전B불가": 0, "문장부족": 0,
                          "프레임불가": 0, "프레임짧음": 0, "세그먼트실패": 0}

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

        # [3] 슬롯 치환: 프레임 리터럴이 모든 문장에 실재해야 한다
        lits = frame_literals(g["form"] or g["pattern"])
        if not lits:
            skipped["프레임불가"] += 1
            continue
        if sum(len(x.split()) for x in lits) < MIN_FRAME_WORDS:
            skipped["프레임짧음"] += 1
            continue
        segd = [segment(x["en"], lits) for x in g["sents"]]
        if any(x is None for x in segd):
            skipped["세그먼트실패"] += 1
            continue

        s1 = g["sents"][0]
        blanked = blank_trigger(s1["en"], g["trigger"])
        if blanked is None:
            skipped["버전B불가"] += 1
            continue
        b_en, b_ans = blanked

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
            "vocabB": {"answer": b_ans, "enLines": [b_en], "koLines": [s1["kr"]],
                       "hint": short_meaning(v["meaning"])},
            "sentence": {"en": s1["en"], "kr": s1["kr"], "trigger": g["trigger"]},
            "pattern": {"form": g["form"] or g["pattern"], "meaning": g["pmean"], "desc": g["pdesc"]},
            # [3] 처음 보는 문장에 같은 프레임을 직접 써보는 단계 (응용예문 전부)
            "frame": lits,
            "baseSegs": segd[0]["segs"],
            "apply": [{"en": x["en"], "kr": x["kr"], **sd}
                      for x, sd in zip(g["sents"][1:], segd[1:])],
            "siblings": g["sents"][1:3],
        })

    items.sort(key=lambda x: (x["rank"], x["level"]))
    if MAX_ITEMS:
        items = items[:MAX_ITEMS]

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


if __name__ == "__main__":
    main()
