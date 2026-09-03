#!/usr/bin/env python3
"""리스닝 핑퐁 대화 CSV → 리뷰용 데이터(JSON) 변환.

AI로 생성한 리스닝 대화 CSV(레포 밖)를 프로토타입이 바로 읽는 JSON으로 만든다.
품질 검토가 목적이라 레벨(A1/A2/B1)별로 샘플만 굽는다(레벨당 LP_REVIEW_N개, 기본 15).

대화 CSV 컬럼: id · 표현(trigger) · 레벨 · 상황(situation) · 순서 · 화자 · 문장(English) ·
번역(한국어) · 정답(O) · 트랩 유형 · 해설. 빈 줄로 대화가 나뉜다. 대화마다
A(순서1)/B퀴즈(순서2)/A(순서3=트리거)/B(4)/A(5)/B(6)/A(7) 구조, B퀴즈는 3지선다.

표현(단어 배열) 단계 데이터는 **표현 CSV**(유기적 통합모드 문장)에서 **같은 id로 조인**해
채운다: 표제어(회화패턴) → 표현 이름, 카드 회색1행(뜻) → 한국어 뜻, 대표 문장(문장1) →
배열 문장. 표현 문장은 리스닝 대사와 다른 문장이라 리스닝을 스포일하지 않는다.
조인 실패한 id 만 noArrange=true 로 표현 단계를 건너뛴다.

사용법: python3 scripts/lp_csv_to_data.py [대화CSV] [표현CSV]
  (기본: env LP_REVIEW_CSV / LP_EXPR_CSV 또는 아래 DEFAULT)
"""
import csv
import json
import os
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "public"
DEFAULT_CSV = os.path.expanduser("~/Downloads/리스닝__누적_.xlsx - 리스닝.csv")
DEFAULT_EXPR_CSV = os.path.expanduser("~/Downloads/유기적 통합모드 문장 (공유용) - 문장 제출(0827).csv")
PER_LEVEL = int(os.environ.get("LP_REVIEW_N", "15"))
# 레벨 → 출력 파일(리뷰용). 프로토타입 DATA_GROUPS 가 이 파일명을 참조한다.
LEVEL_FILES = {"A1": "listening-pingpong.data.rv-a1.json",
               "A2": "listening-pingpong.data.rv-a2.json",
               "B1": "listening-pingpong.data.rv-b1.json"}


def s(v):
    return "" if v is None else str(v).strip()


def read_groups(path):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    hdr = rows[0]
    groups = []          # [(id, [rowdict...])], 원래 순서 유지
    seen = {}
    for row in rows[1:]:
        d = dict(zip(hdr, row))
        gid = s(d["id"])
        if not gid:
            continue
        if gid not in seen:
            seen[gid] = []
            groups.append((gid, seen[gid]))
        seen[gid].append(d)
    return groups


def read_expressions(path):
    """표현 CSV(그룹 헤더에만 값, forward-fill)를 id별로 읽어 표현 단계 데이터를 만든다.
    반환: {id: {pattern, meaning, form, desc, arrange:{en,ko}}}"""
    rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    hdr = rows[0]
    out = {}
    cur = None
    for row in rows[1:]:
        d = dict(zip(hdr, row))
        gid = s(d["id"])
        if gid:
            cur = gid
            out.setdefault(cur, {"pattern": s(d["표제어 또는 회화패턴"]), "meaning": s(d["카드 회색 1행 (뜻)"]),
                                 "form": s(d["카드 초록 (형태)"]), "desc": s(d["카드 회색 2행 (설명)"]),
                                 "arrange": None})
        if cur is None:
            continue
        en, kr = s(d["sentence"]), s(d["translation"])
        if en and out[cur]["arrange"] is None:  # 첫 문장(문장1=트리거 대표 문장) = 배열 문장
            out[cur]["arrange"] = {"en": en, "ko": kr}
    return out


def build_dialogue(g):
    """행들을 A 발화 / B 3지선다 퀴즈로 묶는다(연속 B + 같은 순서 = 한 문제)."""
    turns = []
    i = 0
    while i < len(g):
        r = g[i]
        who = s(r["화자"]).upper()
        if who == "A":
            turns.append({"role": "A", "text": s(r["문장 (English)"]), "kr": s(r["번역 (한국어)"])})
            i += 1
        else:
            order = s(r["순서"])
            choices = []
            while i < len(g) and s(g[i]["화자"]).upper() == "B" and s(g[i]["순서"]) == order:
                o = g[i]
                choices.append({
                    "text": s(o["문장 (English)"]),
                    "kr": s(o["번역 (한국어)"]),
                    "correct": s(o["정답"]).upper() == "O",
                    "trap": s(o["트랩 유형"]) or "정답",
                    "explain": s(o["해설"]),
                })
                i += 1
            turns.append({"role": "B", "choices": choices})
    return turns


def build_example(gid, g, expr):
    head = g[0]
    trigger = s(head["표현(trigger)"])
    ex = {
        "id": int(gid),
        "level": s(head["레벨"]),
        "title": s(head["상황(situation)"]),
        "trigger": trigger,
        "dialogue": build_dialogue(g),
    }
    e = expr.get(gid)
    if e and e.get("arrange") and e["arrange"].get("en"):
        # 표현 CSV 조인 성공 → 표현 단계(단어 배열)를 표현 문장으로 채운다
        ex["expression"] = {"en": e["pattern"] or trigger, "kr": e["meaning"],
                            "form": e["form"], "desc": e["desc"], "arrange": e["arrange"]}
        ex["vocab"] = {"word": e["pattern"] or trigger, "meaning": e["meaning"]}
    else:
        # 조인 실패 → 표현 단계 생략, 트리거만 이름으로
        ex["noArrange"] = True
        ex["expression"] = {"en": trigger, "kr": ""}
        ex["vocab"] = {"word": trigger, "meaning": ""}
    return ex


def sample(lst, n):
    if len(lst) <= n:
        return lst
    step = len(lst) / n
    return [lst[int(k * step)] for k in range(n)]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LP_REVIEW_CSV", DEFAULT_CSV)
    epath = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LP_EXPR_CSV", DEFAULT_EXPR_CSV)
    if not os.path.exists(path):
        sys.exit(f"대화 CSV 없음: {path}")
    expr = read_expressions(epath) if os.path.exists(epath) else {}
    if not expr:
        print(f"(표현 CSV 없음/비어있음: {epath} — 표현 단계는 생략됨)")
    groups = read_groups(path)
    by_level = defaultdict(list)
    for gid, g in groups:
        by_level[s(g[0]["레벨"])].append((gid, g))

    joined_total = 0
    for level, fname in LEVEL_FILES.items():
        picked = sample(by_level.get(level, []), PER_LEVEL)
        examples = [build_example(gid, g, expr) for gid, g in picked]
        joined = sum(1 for ex in examples if not ex.get("noArrange"))
        joined_total += joined
        data = {
            "meta": {"type": "listening-pingpong", "level": level, "source": "review-csv",
                     "triggerTurn": 3, "note": "AI 생성 리스닝 대화 검토용 샘플. 표현 단계는 표현 CSV에서 id 조인."},
            "examples": examples,
        }
        (OUT_DIR / fname).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {fname}  ({len(examples)} 문항, 표현 조인 {joined}/{len(examples)} / 전체 {len(by_level.get(level, []))} at {level})")
    print(f"표현 조인 합계: {joined_total}")


if __name__ == "__main__":
    main()
