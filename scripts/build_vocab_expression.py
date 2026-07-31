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

MAX_ITEMS = int(os.environ.get("VE_MAX_ITEMS", "60"))   # 모드별 문항 수(0이면 전체)
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


def core_text(s):
    """`[...]`로 표시된 핵심 표현 구간의 평문. 표현 데이터에만 있고 문법엔 없다."""
    m = re.search(r"\[([^\]]+)\]", s or "")
    return strip_markup(m.group(1)) if m else ""


def lead_in(s):
    """핵심 표현 앞에 붙은 도입부("Excuse me?", "Yeah," 등). 없으면 빈 문자열."""
    m = re.search(r"\[([^\]]+)\]", s or "")
    return strip_markup((s or "")[: m.start()]) if m else ""


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
    """kind: 'expression' | 'grammar'.

    진입점은 하나이고 문항마다 트리거 어휘와 표현/문법이 모두 달라져야 하므로,
    **패턴(표현 제목 / 문법 소제목)당 1문항만** 뽑아 레벨 오름차순 단일 시퀀스로 만든다.
    (레벨별로 묶으면 같은 패턴이 연속돼 키워드만 바뀌는 반복이 된다.)
    """
    if not csv_path.exists():
        die(f"CSV 없음: {csv_path}")
    rows = list(csv.reader(open(csv_path, newline="", encoding="utf-8")))

    if kind == "expression":
        # unit0, title_en3, title_kr4, sentence15, translation16, content_word26, dictSeq28
        C = dict(level=0, title_en=3, title_kr=4, sentence=15, trans=16, cw=26, seq=28)
    else:
        # level6, sentence10, 번역11, 큰제목21, 소제목22, content_word23, dictSeq25
        C = dict(level=6, sentence=10, trans=11, big=21, sub=22, cw=23, seq=25)

    ncol = max(C.values()) + 1
    # 병합셀(빈칸) forward-fill 대상: 레벨 + (표현: 제목 / 문법: 큰제목·소제목)
    ff_cols = [C["level"]] + ([C["title_en"], C["title_kr"]] if kind == "expression" else [C["big"], C["sub"]])
    ff = {c: "" for c in ff_cols}

    def pattern_key():
        if kind == "expression":
            return (ff[C["title_en"]] or ff[C["title_kr"]]).strip()
        return (ff[C["big"]] + "::" + ff[C["sub"]]).strip(":")

    # 1) 전체 스캔: 패턴별 예문 수집(어휘 조인 성공 여부와 무관) — 활용 규모·응용 예문의 근거
    pattern_examples = {}   # pk -> [{word,en,kr}]
    candidates = []         # 어휘 조인까지 성공한 문항 후보
    prev_big = None
    for r in rows[1:]:
        if len(r) < ncol:
            continue
        # 큰제목이 바뀌면 소제목 forward-fill 리셋(다음 큰제목으로 번지지 않게)
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
        pk = pattern_key()
        if not pk:
            continue
        # 핵심 표현 앞의 군더더기 도입부("Excuse me?", "Yeah," …)가 있는 문장은 제외 —
        # 배열 문장이 표현 자체로 시작해야 학습 대상이 선명하다. (문법엔 마크업이 없어 항상 통과)
        if lead_in(sent):
            continue

        lst = pattern_examples.setdefault(pk, [])
        if not any(x["word"].lower() == cw.lower() for x in lst):
            lst.append({"word": cw, "en": strip_markup(sent), "kr": strip_markup(trans),
                        "coreEn": core_text(sent)})

        seq = r[C["seq"]].strip()
        vocab = vocab_by_seq.get(int(seq)) if seq.isdigit() else None
        if vocab is None:
            continue
        vex = make_vocab_example(vocab)
        if vex is None:
            continue

        s = {"en": strip_markup(sent), "kr": strip_markup(trans), "trigger": cw}
        if kind == "expression":
            s["pattern_en"] = ff[C["title_en"]]
            s["pattern_kr"] = ff[C["title_kr"]]
            s["coreEn"] = core_text(sent)     # 정답 후 하이라이트할 핵심 표현 구간
            s["coreKr"] = core_text(trans)
        else:
            s["pattern_kr"] = ff[C["sub"]] or ff[C["big"]]
            s["big"] = ff[C["big"]]
        candidates.append({
            "pk": pk,
            "level": lv,
            "item": {
                "level": lv,
                "word": vocab["spelling"],
                "meaning": vocab["meaning"],
                "pos": vocab["pos"],
                "cefr": cefr_by_seq.get(int(seq), ""),
                "vocab": vex,
                "sentence": s,
            },
        })

    # 2) 패턴당 1문항 + 어휘 중복 제거 → 레벨 오름차순
    items, seen_pk, seen_word = [], set(), set()
    for c in sorted(candidates, key=lambda x: x["level"]):
        w = c["item"]["word"].lower()
        if c["pk"] in seen_pk or w in seen_word:
            continue
        # 문항 1개 + 응용 예문 2개가 나오는 패턴만 쓴다(보상 카드가 비지 않도록)
        if len(pattern_examples.get(c["pk"], [])) < 3:
            continue
        seen_pk.add(c["pk"]); seen_word.add(w)
        s = c["item"]["sentence"]
        group = pattern_examples.get(c["pk"], [])
        s["siblings"] = [x for x in group if x["word"].lower() != s["trigger"].lower()][:2]
        items.append(c["item"])
        if MAX_ITEMS and len(items) >= MAX_ITEMS:
            break
    return items


def main():
    vocab_by_seq = load_vocab()
    cefr_by_seq = load_gse_cefr()
    expr = build_mode(EXPR_CSV, "expression", vocab_by_seq, cefr_by_seq)
    gram = build_mode(GRAM_CSV, "grammar", vocab_by_seq, cefr_by_seq)

    data = {
        "meta": {
            "type": "vocab-expression",
            "flow": "어휘 빈칸 채우기 → 트리거된 문장 배열",
            "note": "어휘 빈칸(영어 예문의 [단어]=정답, 한국어 번역의 [뜻]=초록 하이라이트) 학습 후, 그 어휘가 트리거하는 표현/문법 문장을 배열. 진입점 하나에 문항마다 어휘·패턴이 모두 다른 단일 시퀀스.",
            "maxItems": MAX_ITEMS,
        },
        "modes": {
            "expression": {"label": "표현", "desc": "관용 표현 문장 배열", "items": expr},
            "grammar": {"label": "문법", "desc": "기초 문법 문장 배열", "items": gram},
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_vocab_expression] 완료 → {OUT}")
    print(f"  표현: {len(expr)}문항 | 문법: {len(gram)}문항 (각 문항 = 서로 다른 패턴)")


if __name__ == "__main__":
    main()
