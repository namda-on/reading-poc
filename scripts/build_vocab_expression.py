#!/usr/bin/env python3
"""어휘(빈칸)→표현/문법(문장 배열) 프로토타입 데이터 생성.

소스(레포 밖, 기본값은 ~/Downloads):
  - 표현 CSV: content_word(트리거 어휘) + sentence(표현 학습 문장) + translation
  - 문법 CSV: content_word + sentence + 번역
  - 어휘 CSV(All_*.csv): seq(=dictSeq) + learnSentence(영어 예문, [단어]=빈칸 정답)
      + learnSentenceMeaning(한국어 번역, [뜻]=초록 하이라이트) + meaning + pos
  - gse xlsx: 어휘 CEFR(corrected_cefr) 보강용

조인: 트리거 CSV의 dictSeq == 어휘 CSV의 seq == gse의 dictSeq.

출력: public/vocab-expression.data.json (커밋되는 생성물, 런타임 유일 소스).
손으로 편집하지 말 것 — 재생성만.
"""
import csv, json, os, re, sys
from pathlib import Path

HOME = Path.home()
DL = HOME / "Downloads"
EXPR_CSV = Path(os.environ.get("VE_EXPR_CSV", DL / "기존 문법_표현_트리거 단어 선정 - 표현_콘텐트워드_추가.csv"))
GRAM_CSV = Path(os.environ.get("VE_GRAM_CSV", DL / "기존 문법_표현_트리거 단어 선정 - 문법_콘텐트워드_추가.csv"))
GSE_XLSX = Path(os.environ.get("VE_GSE_XLSX", DL / "gse_corrected_final_0610.xlsx"))
VOCAB_CSV = Path(os.environ.get("VE_VOCAB_CSV", DL / "All_(2026-07-24_01_54_53).csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "vocab-expression.data.json"

# 부적절/불필요로 표시된 어휘는 제외
VOCAB_FILTER_SKIP = {"sexual", "unnecessary"}

ITEMS_PER_LEVEL = int(os.environ.get("VE_ITEMS_PER_LEVEL", "5"))
MAX_LEVELS = int(os.environ.get("VE_MAX_LEVELS", "30"))  # 표현/문법 모두 구조화된 레벨은 1~30 (표현의 40은 오버플로 버킷)


def die(msg):
    print(f"[build_vocab_expression] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_gse_cefr():
    """gse xlsx에서 dictSeq → CEFR 만 뽑는다(어휘 레벨 배지용)."""
    try:
        import openpyxl
    except ImportError:
        die("openpyxl 필요: pip install openpyxl")
    if not GSE_XLSX.exists():
        die(f"gse xlsx 없음: {GSE_XLSX} (VE_GSE_XLSX로 지정)")
    wb = openpyxl.load_workbook(GSE_XLSX, read_only=True, data_only=True)
    ws = wb["보정결과_전체"]
    it = ws.iter_rows(values_only=True)
    next(it)
    cefr = {}
    for r in it:
        seq = r[20]  # dictSeq
        if seq is not None and seq not in cefr:
            cefr[seq] = (r[7] or "").strip()  # corrected_cefr
    return cefr


def clean_meaning(m):
    """어휘 뜻 정리: 첫 줄만 사용하고 선두 ⓜ 등 마커·앞뒤 공백 제거."""
    first = (m or "").split("\n")[0]
    return re.sub(r"^[^\w가-힣<(]+", "", first.strip()).strip()


def load_vocab():
    """어휘 CSV → seq(dictSeq) → {spelling, pos, meaning, learnSentence, learnSentenceMeaning}."""
    if not VOCAB_CSV.exists():
        die(f"어휘 CSV 없음: {VOCAB_CSV} (VE_VOCAB_CSV로 지정)")
    rows = list(csv.reader(open(VOCAB_CSV, newline="", encoding="utf-8")))
    # seq0, rank1, spelling2, pos3, meaning4, learnSentence5, learnSentenceMeaning6, edit7, filter8
    by_seq = {}
    for r in rows[1:]:
        if len(r) < 9:
            continue
        seq = r[0].strip()
        if not seq.isdigit() or seq in by_seq:
            continue
        if r[8].strip() in VOCAB_FILTER_SKIP:
            continue
        ls, lsm = r[5].strip(), r[6].strip()
        if not (ls and lsm):
            continue
        by_seq[int(seq)] = {
            "spelling": r[2].strip(),
            "pos": (r[3].split("\n")[0]).strip(),  # 영어 품사만
            "meaning": clean_meaning(r[4]),
            "learnSentence": ls,
            "learnSentenceMeaning": lsm,
        }
    return by_seq


def strip_markup(s):
    """표현/문법 sentence의 [...] {...} 마크업 제거 → 배열용 평문."""
    return s.replace("[", "").replace("]", "").replace("{", "").replace("}", "").strip()


BRACKET = re.compile(r"\[([^\]]+)\]")


def _norm(s):
    return re.sub(r"[^a-z0-9' ]", "", s.lower()).strip()


def make_vocab_example(vocab):
    """어휘 CSV 행 → {answer, enLines, koLines}.

    - enLines: 영어 예문 줄들([단어]=빈칸 마크업 보존). 첫 [단어]가 빈칸 정답.
    - koLines: 한국어 번역 줄들([뜻]=초록 하이라이트 마크업 보존). 괄호 설명줄 포함.
    - answer(영어 빈칸)는 학습 대상 표제어와 동일해야 한다(굴절형·부분구 예문 제외).
    """
    m = BRACKET.search(vocab["learnSentence"])
    if not m:
        return None
    answer = m.group(1).strip()
    if not answer or _norm(answer) != _norm(vocab["spelling"]):
        return None
    return {
        "answer": answer,
        "enLines": [ln.strip() for ln in vocab["learnSentence"].split("\n")],
        "koLines": [ln.strip() for ln in vocab["learnSentenceMeaning"].split("\n")],
    }


def clean_choices(cell):
    """객관식 선택지 셀(줄바꿈/구분자) → 리스트. 배열 방해 타일 후보."""
    if not cell:
        return []
    parts = re.split(r"[\n/;]|,", cell)
    return [p.strip() for p in parts if p.strip()]


def build_mode(csv_path, kind, vocab_by_seq, cefr_by_seq):
    """kind: 'expression' | 'grammar'. 레벨별 그룹으로 아이템 추출."""
    if not csv_path.exists():
        die(f"CSV 없음: {csv_path}")
    rows = list(csv.reader(open(csv_path, newline="", encoding="utf-8")))

    if kind == "expression":
        # unit0, id2, title_en3, title_kr4, cat5, sentence15, translation16, content_word26, dictSeq28
        C = dict(level=0, title_en=3, title_kr=4, cat=5, sentence=15, trans=16, cw=26, seq=28)
    else:
        # level6, sentence10, 번역11, 큰제목21, 소제목22, content_word23, dictSeq25
        C = dict(level=6, sentence=10, trans=11, big=21, sub=22, cw=23, seq=25)

    ncol = max(C.values()) + 1
    # 병합셀(빈칸) forward-fill 대상 컬럼: 레벨 + (표현: 카테고리·표현 제목 / 문법: 큰제목·소제목)
    ff_cols = [C["level"]] + ([C["cat"], C["title_en"], C["title_kr"]] if kind == "expression" else [C["big"], C["sub"]])
    ff = {c: "" for c in ff_cols}

    # 패턴별 필러(트리거 단어) 수집 → 정답 후 '다른 단어도 이렇게 써요' 일반화용
    pattern_fillers = {}  # patternKey -> [content_word ...] (등장순, 중복 제거)

    def pattern_key():
        if kind == "expression":
            return (ff[C["title_en"]] or ff[C["title_kr"]]).strip()
        return (ff[C["big"]] + "::" + ff[C["sub"]]).strip("::")

    levels = {}   # level -> {items, seen, ...}
    all_items = []
    prev_big = None
    for r in rows[1:]:
        if len(r) < ncol:
            continue
        # 큰제목이 바뀌면 소제목 forward-fill을 리셋(다음 큰제목으로 번지지 않게)
        if kind == "grammar" and r[C["big"]].strip() and r[C["big"]].strip() != prev_big:
            prev_big = r[C["big"]].strip()
            if not r[C["sub"]].strip():
                ff[C["sub"]] = ""
        for c in ff_cols:
            if r[c].strip():
                ff[c] = r[c].strip()
        level = ff[C["level"]]
        if not (level and level.isdigit()):
            continue
        lv = int(level)
        if lv < 1 or lv > MAX_LEVELS:
            continue

        cw = r[C["cw"]].strip()
        sent = r[C["sentence"]].strip()
        trans = r[C["trans"]].strip()
        if not (cw and sent and trans):
            continue

        # 어휘 CSV 조인 (dictSeq == seq)
        seq = r[C["seq"]].strip()
        vocab = vocab_by_seq.get(int(seq)) if seq.isdigit() else None
        if vocab is None:
            continue
        vex = make_vocab_example(vocab)
        if vex is None:
            continue

        # 패턴별 예문 누적(레벨 상한과 무관하게 전체 스캔에서 모음) — 정답 후 '이렇게도 써요' 응용 예문용
        pk = pattern_key()
        if pk:
            lst = pattern_fillers.setdefault(pk, [])
            if not any(x["word"].lower() == cw.lower() for x in lst):
                lst.append({"word": cw, "en": strip_markup(sent), "kr": strip_markup(trans)})

        bucket = levels.setdefault(lv, {"items": [], "seen": set()})
        if len(bucket["items"]) >= ITEMS_PER_LEVEL:
            continue
        if cw.lower() in bucket["seen"]:
            continue
        bucket["seen"].add(cw.lower())

        s = {
            "en": strip_markup(sent),
            "kr": strip_markup(trans),
            "trigger": cw,
            "_pk": pk,
        }
        if kind == "expression":
            s["pattern_en"] = ff[C["title_en"]]
            s["pattern_kr"] = ff[C["title_kr"]]
            s["category"] = ff[C["cat"]]
        else:
            s["pattern_kr"] = ff[C["sub"]] or ff[C["big"]]
            s["big"] = ff[C["big"]]
        item = {
            "word": vocab["spelling"],
            "meaning": vocab["meaning"],
            "pos": vocab["pos"],
            "cefr": cefr_by_seq.get(int(seq), ""),
            "vocab": vex,
            "sentence": s,
        }
        bucket["items"].append(item)
        all_items.append(item)

    # 같은 패턴의 다른 예문(en+kr)을 최대 3개 붙인다(자기 자신 제외) — 응용 예문
    for it in all_items:
        s = it["sentence"]
        pk = s.pop("_pk", "")
        sibs = [x for x in pattern_fillers.get(pk, []) if x["word"].lower() != s["trigger"].lower()]
        s["siblings"] = sibs[:3]

    out_levels = []
    for lv in sorted(levels):
        b = levels[lv]
        if not b["items"]:
            continue
        sublabel = b["items"][0]["sentence"].get("big", "") if kind == "grammar" else ""
        out_levels.append({
            "level": lv,
            "label": f"레벨 {lv}",
            "sublabel": sublabel,
            "items": b["items"],
        })
    return out_levels


def main():
    vocab_by_seq = load_vocab()
    cefr_by_seq = load_gse_cefr()
    expr = build_mode(EXPR_CSV, "expression", vocab_by_seq, cefr_by_seq)
    gram = build_mode(GRAM_CSV, "grammar", vocab_by_seq, cefr_by_seq)

    data = {
        "meta": {
            "type": "vocab-expression",
            "flow": "어휘 빈칸 채우기 → 트리거된 문장 배열",
            "note": "어휘 빈칸(영어 예문의 [단어]=정답, 한국어 번역의 [뜻]=초록 하이라이트) 학습 후, 그 어휘가 트리거하는 표현/문법 문장을 배열.",
            "itemsPerLevel": ITEMS_PER_LEVEL,
        },
        "modes": {
            "expression": {"label": "표현", "desc": "관용 표현 문장 배열", "levels": expr},
            "grammar": {"label": "문법", "desc": "기초 문법 문장 배열", "levels": gram},
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ec = sum(len(l["items"]) for l in expr)
    gc = sum(len(l["items"]) for l in gram)
    print(f"[build_vocab_expression] 완료 → {OUT}")
    print(f"  표현: {len(expr)}레벨 {ec}아이템 | 문법: {len(gram)}레벨 {gc}아이템")


if __name__ == "__main__":
    main()
