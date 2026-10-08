"""확정 CSV의 901유닛을 기획 검토용으로 정리한다 — ① 한 유닛에 갈래가 섞인 것을 나누고 ② 나눈 뒤 유닛마다 패턴화 가능/불가를 판정한다.
소스(레포 밖): UNITS_CSV(classify_units.py 와 같은 확정 CSV) · CONCERN_CSV(기본 ~/Downloads/패턴화 고민 목록 - 목록.csv)
산출: public/units/ 아래 CSV 세 장 — 배포 사이트에서 서빙되므로 Google 시트가 IMPORTDATA 로 바로 불러온다(BOM 을 붙이면 첫 칸에 섞여 들어간다)
  열 이름 앞에 출처를 붙인다 — `원본 ·` 확정 CSV 그대로 · `변경 ·` 원본을 바꾸자는 제안(나눈 유닛뿐) · `추가 ·` 원본에 없던 판정 · `채움 ·` 원본에 빈 열로 있던 것
  units-after-split.gen.csv      확정 CSV 의 문장 행 전부(순서·내용 그대로) + 오른쪽에 변경·추가 열
  unit-splits.gen.csv            나눈 26유닛만 — 원본 문장을 새 유닛별로 묶어 원본 태그와 새 태그를 나란히
  pattern-concern-list.judged.gen.csv  고민 목록 133유닛 그대로 + 빈 열이던 '패턴 학습 포인트'·'판단'을 채움

나누는 기준: 갈래마다 뜻이나 쓰는 자리가 달라 따로 골라야 하는 것(stop -ing / stop to, some / any, at / on / in …)과
카드 초록에 틀이 둘 적힌 것. 같은 자리에 같은 부류 낱말이 갈아 끼워지는 열린 목록(의문사·감각동사·접속사),
주어에 맞춰 정해지는 것(myself / yourself, 부가의문문), 뉘앙스 차이(can / could)는 나누지 않는다 — KEEP 에 이유를 적는다.
"""
import csv, json, os, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classify_units as cu

CONCERN = Path(os.environ.get("CONCERN_CSV", cu.DL / "패턴화 고민 목록 - 목록.csv"))
OUT = Path(__file__).resolve().parent.parent / "public" / "units"
VARIANT = ("문장1-2", "문장1-3")
BASIC = ("기본", "문장1", "문장2", "문장3")

# 나눌 유닛 — 갈래 키 → (새 카드 초록, 새 뜻). 갈래 키는 분류기의 쪽 라벨(by=side)·동사+꼴(by=verb)·틀(by=frame)이다.
SPLITS = {
  "10019": ("side", "장소 전치사가 갈래마다 뜻이 다르다", {
    "in": ("주어 + be동사 + in + ______ .", "~ 안에 있어"), "on": ("주어 + be동사 + on + ______ .", "~ 위에 있어"),
    "at": ("주어 + be동사 + at + ______ .", "~에 있어")}),
  "10059": ("side", "때를 나타내는 전치사가 갈래마다 붙는 말이 다르다", {
    "on": ("on + 요일·날짜", "~에 (요일·날짜)"), "at": ("at + 시각", "~시에"), "in": ("in + 아침·달·계절", "~에 (아침·달·계절)")}),
  "10083": ("side", "긍정문 some / 부정·의문문 any", {
    "some": ("some ______", "좀 ~"), "any": ("not any ______ / any ______ ?", "~가 하나도 없는 / ~ 있어?")}),
  "10117": ("side", "긍정문 some / 부정·의문문 any", {
    "some": ("some of ______", "~ 중 몇몇"), "any": ("any (of) ______", "~ 중 아무거나 / 하나도")}),
  "10097": ("side", "셀 수 있는 many / 셀 수 없는 much", {
    "many": ("How many ______ ?", "~가 몇 개야?"), "much": ("How much ______ ?", "~가 얼마나 돼?")}),
  "10098": ("side", "셀 수 있는 many / 셀 수 없는 much", {
    "much": ("not much ______", "~가 많지 않아 (셀 수 없는 것)"), "many": ("not many ______", "~가 많지 않아 (셀 수 있는 것)")}),
  "10180": ("side", "셀 수 있는 a few / 셀 수 없는 a little", {
    "few": ("a few ______", "몇 개의 ~"), "little": ("a little ______", "조금의 ~")}),
  "10186": ("side", "셀 수 있는 few / 셀 수 없는 little", {
    "few": ("few ______", "~가 거의 없어 (셀 수 있는 것)"), "little": ("little ______", "~가 거의 없어 (셀 수 없는 것)")}),
  "10102": ("side", "긍정 too / 부정 either", {
    "too": ("______ , too.", "나도 ~해"), "either": ("______ not ~ , either.", "나도 안 해")}),
  "10137": ("side", "금지 must not / 불필요 don't have to — 뜻이 정반대다", {
    "must": ("must not ______", "~하면 안 돼"), "to": ("don't have to ______", "~ 안 해도 돼")}),
  "10127": ("side", "동사마다 for / to 가 갈린다", {
    "for": ("주어 + 동사 + 목적어 + for + 사람 .", "~에게 ~를 해주다 (got·made·bought)"),
    "to": ("주어 + 동사 + 목적어 + to + 사람 .", "~에게 ~를 건네다 (passed·sent)")}),
  "10349": ("side", "or 와 and 의 뜻이 정반대다", {
    "or": ("명령문 , or ______", "~해, 안 그러면 ~"), "and": ("명령문 , and ______", "~하면 ~할 거야")}),
  "10341": ("side", "단수 another / 복수 other", {
    "another": ("another ______", "또 하나의 ~"), "other": ("other ______s", "다른 ~들")}),
  "10402": ("side", "사물·사건 which / 사람 who", {
    "which": ("______ , which + 동사 …", "~했는데, 그게 ~해"), "who": ("사람 , who + 동사 …", "~인데, 그 사람은 ~해")}),
  "10406": ("side", "사물 which / 사람 whom", {
    "which": ("전치사 + which + 주어 + 동사", "~가 ~한 그 (곳·것)"), "whom": ("전치사 + whom + 주어 + 동사", "~가 ~한 그 사람")}),
  "10312": ("side", "능동 -ing / 수동 과거분사", {
    "V-ed": ("______(과거분사) + 명사", "~된 ~"), "V-ing": ("______(현재분사) + 명사", "~하는 ~")}),
  "10313": ("side", "감정을 일으키는 -ing / 느끼는 -ed", {
    "V-ing": ("사물 + be동사 + ______ -ing", "~가 흥미로워 (감정을 일으켜)"), "V-ed": ("사람 + be동사 + ______ -ed", "~가 흥미를 느껴 (내가 느껴)")}),
  "10376": ("side", "능동 -ing / 수동 과거분사", {
    "V-ing": ("______ -ing , 주어 + 동사 .", "~하면서 ~해"), "V-ed": ("______(과거분사) , 주어 + 동사 .", "~돼서 ~해")}),
  "10378": ("side", "능동 -ing / 수동 과거분사", {
    "V-ing": ("with + 명사 + ______ -ing", "~가 ~하는 채로"), "V-ed": ("with + 명사 + ______(과거분사)", "~가 ~된 채로")}),
  "10400": ("side", "능동 -ing / 수동 과거분사", {
    "V-ed": ("명사 + ______(과거분사)", "~된 ~"), "V-ing": ("명사 + ______ -ing", "~하는 ~")}),
  "10369": ("verb", "동사가 다르고, 같은 동사도 -ing / to 에 따라 뜻이 정반대다", {
    "stop V-ing": ("stop ______ -ing", "~하던 걸 멈추다"), "stop to-V": ("stop to ______", "~하려고 멈추다"),
    "regret V-ing": ("regret ______ -ing", "~한 걸 후회하다"), "remember to-V": ("remember to ______", "~할 걸 기억하다"),
    "remember V-ing": ("remember ______ -ing", "~한 걸 기억하다"), "forget V-ing": ("forget ______ -ing", "~한 걸 잊다")}),
  "10026": ("frame", "카드 초록에 틀이 둘이다", {
    "base": ("Let's ______ .", "~하자"), "go": ("Let's go ______ -ing .", "~하러 가자")}),
  "10335": ("frame", "카드 초록에 틀이 둘이다(묻기 / 청하기)", {
    "base": ("Would you like ______ ?", "~ 드릴까요?"), "st": ("I'd like ______ .", "~ 주세요")}),
  "10337": ("frame", "카드 초록에 틀이 둘이다(묻기 / 청하기)", {
    "base": ("Would you like to ______ ?", "~하시겠어요?"), "st": ("I'd like to ______ .", "~하고 싶어요")}),
  "10355": ("frame", "카드 초록에 틀이 둘이다", {
    "base": ("There is no ______ .", "~가 전혀 없어"), "have": ("주어 + have no ______", "(가진) ~가 전혀 없어")}),
  "10439": ("frame", "문장에 틀이 둘이다(don't know if / not sure if)", {
    "base": ("I don't know if ______ .", "~인지 모르겠어"), "sure": ("I'm not sure if ______ .", "~인지 잘 모르겠어")}),
}
FRAME_RX = {"10026": [("go", r"\bgo\b")], "10335": [("st", r"\b(i|we)'d\b")], "10337": [("st", r"\b(i|we)'d\b")],
            "10355": [("have", r"\b(have|has)\b")], "10439": [("sure", r"\bsure\b")]}

# 나누지 않는 대비형 — 갈래가 있어도 한 유닛으로 두는 이유
KEEP = {
  **{k: "열린 목록 — 같은 자리에 의문사가 갈아 끼워진다" for k in ("10013", "10014", "10080")},
  **{k: "열린 목록 — 같은 자리에 같은 부류 낱말(부사·동사·대명사)이 갈아 끼워진다" for k in ("10031", "10037", "10054", "10114", "10195", "10196", "10206")},
  **{k: "열린 목록 — 같은 자리에 접속사·관계사가 갈아 끼워진다" for k in ("10383", "10391", "10396", "10397", "10403")},
  **{k: "열린 목록 — 지시어(this / that / these / those). 단수·복수와 거리로 고르는 대비로 보면 나눌 수 있다(확인 필요)" for k in ("10017", "10020")},
  **{k: "주어에 맞춰 정해진다 — 고르는 결정이 아니다" for k in ("10060", "10088", "10353", "10212")},
  **{k: "뉘앙스 차이 — 갈래의 뜻이 거의 같아 설명(회색 2행)으로 다룬다" for k in ("10066", "10078", "10130", "10189", "10414")},
}

RULE = {"변화형": "형태 규칙 — 같은 규칙으로 낱말마다 끝 모양을 바꾼다(공통된 말이 없다)",
        "자리형": "자리 규칙 — 부사·대명사가 들어가는 위치만 같다(들어가는 낱말은 매번 다르다)",
        "구조형": "어순 규칙 — 고정된 말 없이 덩어리 순서만 같다",
        "해당없음": "해당없음 — 시각 읽기"}

def keys_of(text):
    """문장(또는 카드 초록)의 낱말을 비교용 키로 — 열린 낱말은 줄기, 나머지는 표면형(is / are 는 다르다)"""
    return [(cu.stem(w) if c == "OPEN" else w, c) for w, c in cu.tokens("[" + text + "]")]

def anchors(form, sents):
    """유닛의 모든 문장에 들어 있는 고정된 말(키와 분류).
    후보는 카드 초록의 낱말 + S1 초록의 기능어다 — 문장이 한두 개뿐인 갈래에서 슬롯 낱말(eating)이나 주어(They)가
    우연히 공통으로 잡히지 않게, 열린 낱말·인칭대명사는 카드 초록에 적힌 것만 인정한다.
    be·do·have·인칭대명사는 모든 문장에 같은 꼴로 있어야 인정한다(is / are 가 섞이면 일치 규칙이지 고정된 말이 아니다)."""
    form_keys = keys_of(" ".join(re.findall(r"[A-Za-z']+", form)))
    in_form = {k for k, _ in form_keys}
    s1_keys = keys_of(" ".join(re.findall(r"\[([^\]]+)\]", sents[0][1])))
    cand, seen = [], set()
    for k, c in s1_keys + form_keys:
        if k in cu.ARTICLE or k in seen or c == "POSS": continue
        if c in ("OPEN", "PERS", "BE", "DO", "HAVE") and k not in in_form: continue
        seen.add(k); cand.append((k, c))
    # 카드 초록에 be·do·have 가 하나만 적혀 있으면(have a point) 그 동사는 고정이고 꼴(has / had)만 주어·시제를 따른다.
    # 둘 이상 적혀 있으면(Are / Is + 주어) 고르는 것 자체가 일치 규칙이라 고정어가 아니다.
    family = {c: {k for k, cc in form_keys if cc == c} for c in ("BE", "DO", "HAVE")}
    sent_keys = [keys_of(re.sub(r"[\[\]]", "", e)) for _, e, _ in sents]
    def hit(k, c):
        if c in family and len(family[c]) == 1: return sum(any(cc == c for _, cc in ks) for ks in sent_keys)
        return sum(any(kk == k for kk, _ in ks) for ks in sent_keys)
    out = [(k, c) for k, c in cand
           if hit(k, c) / len(sents) >= (1.0 if c in ("PERS", "BE", "DO", "HAVE") else 0.8)]
    return out if any(c != "PERS" for _, c in out) else []

def surface(anc, sents):
    """키를 S1 에 실제로 쓰인 낱말로 되돌려 S1 의 순서대로 잇는다 — 떨어져 있으면 … (Would … like)"""
    words = re.findall(r"[A-Za-z']+", re.sub(r"[\[\]]", "", sents[0][1]))
    pos = []
    for k, c in anc:
        i = next((i for i, w in enumerate(words) if any(kk == k for kk, _ in keys_of(w))), None)
        if i is None and c in ("BE", "DO", "HAVE"):
            i = next((i for i, w in enumerate(words) if any(cc == c for _, cc in keys_of(w))), None)
        if i is not None and i not in pos: pos.append(i)
    # be·do·have 가 주어와 붙은 꼴(She's · I'm)이면 주어까지 고정어로 보이므로 동사 이름으로 적는다
    label = {}
    for k, c in anc:
        if c in ("BE", "DO", "HAVE"):
            for i in pos:
                ks = keys_of(words[i])
                if any(cc == c for _, cc in ks) and any(cc == "PERS" for _, cc in ks):
                    label[i] = {"BE": "be", "DO": "do", "HAVE": "have"}[c]
    pos.sort()
    out = ""
    for n, i in enumerate(pos):
        out += ("" if n == 0 else (" " if i == pos[n - 1] + 1 else " … ")) + label.get(i, words[i])
    return out

def group_key(uid, by, sent, lab):
    if by == "frame":
        g = " ".join(re.findall(r"\[([^\]]+)\]", sent)).lower()
        return next((n for n, rx in FRAME_RX[uid] if re.search(rx, g)), "base")
    if by == "verb":
        verb = re.findall(r"([A-Za-z']+)\s+\[", sent)[-1].lower()
        return f"{cu.stem(verb)} {lab}"
    return lab

def split_unit(u, gen):
    by, why, spec = SPLITS[u["id"]]
    lab = {i: gen["labels"][k] for k, i in enumerate(gen["indep"])}
    groups = {}
    for i, s in enumerate(u["sents"]):
        side = lab.get(i, lab[0])  # 주어 변형은 S1 쪽으로 간다
        groups.setdefault(group_key(u["id"], by, s[1], side), []).append(s)
    order = sorted(groups, key=lambda k: (u["sents"][0] not in groups[k], -len(groups[k])))
    out = []
    for n, key in enumerate(order):
        if key not in spec: cu.die(f"{u['id']} 갈래 {key} 의 카드 초록이 SPLITS 에 없다")
        form, mean = spec[key]
        ss = groups[key]
        has_s1 = u["sents"][0] in ss
        if not has_s1:  # 원래 S1 이 없는 갈래는 첫 기본 문장을 S1 으로 세운다
            first = next((s for s in ss if s[0] in BASIC), ss[0])
            ss = [first] + [s for s in ss if s is not first]
        out.append(dict(id=f"{u['id']}-{'ABCDEFG'[n]}", parent=u["id"], side=key, why=why, form=form, mean=mean, desc=u["desc"],
                        sents=ss, new_s1=not has_s1))
    return out

WEAK = ("FUNC", "MODAL", "NEG", "BE", "DO", "HAVE", "PERS")

def judge(form, sents, typ=None, side=None, keep=""):
    """→ (패턴화, 공통 고정어, 불가 이유, 확인 메모)"""
    if typ in RULE: return "불가", "", RULE[typ], ""
    anc = anchors(form, sents)
    if anc:
        weak = len(anc) == 1 and anc[0][1] in WEAK
        return "가능", surface(anc, sents), "", ("고정어가 기능어 하나뿐 — 공통 패턴 찾기로는 약하다" if weak else "")
    if side in ("V-ing", "V-ed"):
        return "불가", "", "형태 규칙 — 현재분사(-ing)·과거분사 꼴만 같고 들어가는 낱말은 매번 다르다", ""
    if keep: return "불가", "", keep, ""
    indep = [s for s in sents if s[0] not in VARIANT]
    agree = all(any(c in ("BE", "DO", "HAVE", "MODAL") for _, c in cu.tokens(e)) for _, e, _ in indep)
    return "불가", "", ("일치 규칙 — be·do 와 주어·시제가 문장마다 바뀌어 고정된 말이 없다" if agree
                       else "열린 목록 — 같은 자리에 다른 낱말이 들어가 고정된 말이 없다"), ""

def subj_in_bracket(sents):
    """괄호가 주어까지 묶었는가 — 결정이 일어나는 낱말보다 넓게 칠해진 경우(I didn't / she didn't)"""
    n = 0
    for _, e, _ in sents:
        t = cu.tokens(e)
        if t and t[0][1] == "PERS" and len(t) > 1: n += 1
    return n / len(sents) >= 0.5

XLSX = "unit-organize.gen.xlsx"
NEW_SENTS = Path(__file__).resolve().parent / "unit_split_sentences.json"
SLOTS = ["S1", "문장1-2", "문장1-3", "기본", "기본", "어려운", "어려운", "어려운"]  # 나눈 26유닛의 원래 구성과 같다

def full_set(p, written):
    """새 유닛의 8칸 — 원래 유닛의 문장을 먼저 원래 칸에 넣고, 빈칸만 새로 쓴 문장으로 채운다"""
    pool = {k: [] for k in SLOTS}
    for t, e, k in p["sents"][1:]: pool.setdefault(t, []).append((e, k, "기존", t))
    for t, e, k in written.get(p["id"], []): pool.setdefault(t, []).append((e, k, "새로 씀", ""))
    s1 = p["sents"][0]
    rows = [("S1", s1[1], s1[2], "기존", s1[0])]
    for slot in SLOTS[1:]:
        if not pool.get(slot): cu.die(f"{p['id']} 의 {slot} 칸이 비었다 — {NEW_SENTS.name} 에 채워야 한다")
        e, k, src, orig = pool[slot].pop(0)
        rows.append((slot, e, k, src, orig))
    left = [x for v in pool.values() for x in v]
    if left: cu.die(f"{p['id']} 에 칸보다 문장이 많다: {left}")
    return rows

def write_xlsx(units, recs, blocks, concern_rows, judged):
    """기획 검토용 엑셀 — 원본(회색) · 변경 제안(주황) · 추가 판정(파랑) · 채움(초록)을 색으로 가른다.
    요약 숫자는 각 탭을 세는 수식이다(탭을 고치면 따라 바뀐다)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    GRAY, ORANGE, BLUE, GREEN, PURPLE = "EEF1F5", "FDEBD6", "E1EDFB", "E2F4E7", "EEE6FB"
    DARK = {GRAY: "5D6B7D", ORANGE: "A85A12", BLUE: "2F5E9E", GREEN: "2C7A47", PURPLE: "6A3FB5"}
    F = lambda **k: Font(name="Arial", size=k.pop("size", 10), **k)
    fill = lambda c: PatternFill("solid", fgColor=c)
    thin, thick = Side(style="thin", color="D5DBE3"), Side(style="medium", color="8A97A8")
    wrap = Alignment(wrap_text=True, vertical="top")

    def table(ws, groups, widths, rows, row_style=None):
        """1행: 출처 띠(병합) · 2행: 열 이름 · 3행부터 데이터"""
        col = 1
        for label, color, names in groups:
            ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + len(names) - 1)
            c = ws.cell(1, col, label); c.fill = fill(color); c.font = F(bold=True, color=DARK[color]); c.alignment = Alignment(vertical="center")
            for k, n in enumerate(names):
                h = ws.cell(2, col + k, n); h.fill = fill(color); h.font = F(bold=True, color=DARK[color]); h.alignment = wrap
                h.border = Border(bottom=thick)
            col += len(names)
        for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
        for r, row in enumerate(rows, 3):
            for c, v in enumerate(row, 1):
                cell = ws.cell(r, c, v); cell.font = F(); cell.alignment = wrap
            if row_style: row_style(ws, r, row)
        ws.freeze_panes = "B3"
        ws.auto_filter.ref = f"A2:{get_column_letter(len(widths))}{len(rows) + 2}"
        ws.row_dimensions[1].height = 20; ws.row_dimensions[2].height = 30

    wb = Workbook()
    readme = wb.active; readme.title = "읽는 법"
    written = json.load(open(NEW_SENTS, encoding="utf-8"))

    # ── 나눈 유닛: 원본 유닛 블록마다 원본 → 새 유닛을 옆으로 나란히 ──
    ws = wb.create_sheet("나눈 유닛")
    rows, marks = [], []  # marks: (행 종류) — 원본 유닛 첫 행 / 새 유닛 첫 행 / S1 이 바뀐 행
    for u, parts in blocks:
        for pi, p in enumerate(parts):
            indep = [x for x in p["sents"] if x[0] not in VARIANT]
            memo = []
            if p["new_s1"]: memo.append("S1 새로 지정(주어 변형 없음)")
            memo.append(f"원래 문장 {len(p['sents'])}개 + 새로 쓴 문장 {len(written.get(p['id'], []))}개 = 8칸")
            for k, (tag, en, kr) in enumerate(p["sents"]):
                orig_s1 = p["sents"][k] is u["sents"][0]
                new_tag = ("S1" if orig_s1 else "S1 ← " + tag) if k == 0 else ""
                rows.append([u["id"] if pi == 0 and k == 0 else "", u["form"] if pi == 0 and k == 0 else "", u["mean"] if pi == 0 and k == 0 else "",
                             tag, en, kr, p["id"] if k == 0 else "", p["form"] if k == 0 else "", p["mean"] if k == 0 else "", new_tag,
                             p["why"] if pi == 0 and k == 0 else "", " · ".join(memo) if k == 0 else ""])
                marks.append(("unit" if pi == 0 and k == 0 else "part" if k == 0 else "", k == 0 and not orig_s1))
    def split_style(ws, r, row):
        kind, s1_changed = marks[r - 3]
        if kind:
            for c in range(1, 13): ws.cell(r, c).border = Border(top=thick if kind == "unit" else thin)
        for c in (1, 2, 3): ws.cell(r, c).font = F(bold=True)
        for c in (7, 8, 9): ws.cell(r, c).fill = fill(ORANGE) if row[6] else PatternFill()
        if row[6]: ws.cell(r, 7).font = F(bold=True, color=DARK[ORANGE])
        if s1_changed: ws.cell(r, 10).font = F(bold=True, color=DARK[ORANGE])
        if row[11]: ws.cell(r, 12).font = F(color=DARK[PURPLE])
    table(ws, [("원본 유닛 (확정 CSV 그대로)", GRAY, ["원본 id", "원본 카드 초록", "원본 뜻"]),
               ("원본 문장 (확정 CSV 그대로)", GRAY, ["원본 태그", "sentence", "translation"]),
               ("변경 제안 — 나눈 새 유닛", ORANGE, ["새 유닛", "새 카드 초록", "새 뜻", "새 태그"]),
               ("판단 근거 (추가)", BLUE, ["나누는 이유", "메모"])],
          [9, 22, 18, 9, 38, 30, 10, 22, 18, 13, 26, 24], rows, split_style)

    # ── 나눈 유닛 문장: 새 유닛마다 8칸, 기존 문장(회색)과 새로 쓴 문장(보라)을 가른다 ──
    ws = wb.create_sheet("나눈 유닛 문장")
    rows, starts = [], []
    for u, parts in blocks:
        for p in parts:
            for k, (slot, en, kr, src, orig) in enumerate(full_set(p, written)):
                starts.append(k == 0)
                rows.append([p["id"] if k == 0 else "", p["form"] if k == 0 else "", p["mean"] if k == 0 else "", slot, en, kr, src,
                             f"{u['id']} · {orig}" if src == "기존" else ""])
    def sent_style(ws, r, row):
        if starts[r - 3]:
            for c in range(1, 9): ws.cell(r, c).border = Border(top=thick)
            for c in (1, 2, 3): ws.cell(r, c).fill = fill(ORANGE); ws.cell(r, c).font = F(bold=True, color=DARK[ORANGE])
        new = row[6] == "새로 씀"
        for c in (4, 5, 6, 7): ws.cell(r, c).fill = fill(PURPLE if new else GRAY)
        ws.cell(r, 7).font = F(bold=True, color=DARK[PURPLE] if new else DARK[GRAY])
    table(ws, [("새 유닛 (변경 제안)", ORANGE, ["새 유닛", "카드 초록", "뜻"]),
               ("학습 문장 — 기존(회색) / 새로 씀(보라)", PURPLE, ["칸", "sentence", "translation", "출처", "원래 유닛 · 원래 칸"])],
          [9, 22, 18, 9, 44, 36, 9, 16], rows, sent_style)

    # ── 유닛별 판정: 나눈 뒤 유닛 한 줄씩 ──
    ws = wb.create_sheet("유닛별 판정")
    rows = [[r["orig"], r["new"], r["form"], r["mean"], r["s1"], r["typ"], r["pat"], r["anc"] or r["why"], r["chk"], r["reason"], r["memo"], r["concern"]] for r in recs]
    def judge_style(ws, r, row):
        if row[1]:
            for c in (2, 3, 4): ws.cell(r, c).fill = fill(ORANGE)
        ws.cell(r, 7).font = F(bold=True, color="2C7A47" if row[6] == "가능" else "B0603A")
        if row[8]: ws.cell(r, 9).font = F(color="B0603A")
    table(ws, [("원본 (나눈 유닛은 원본 id 만 원본 — 새 유닛·카드 초록·뜻은 주황 = 제안)", GRAY, ["원본 id", "새 유닛", "카드 초록", "뜻", "S1 문장"]),
               ("판정 (추가)", BLUE, ["유형", "패턴화", "공통 고정어 / 불가 이유", "확인", "나누거나 남긴 이유", "메모", "고민 목록 유형"])],
          [9, 9, 24, 18, 34, 13, 8, 34, 22, 30, 22, 16], rows, judge_style)

    # ── 고민 목록 판단: 채운 두 열을 앞으로 당겨 보이게 한다(값은 그대로) ──
    ws = wb.create_sheet("고민 목록 판단")
    head = concern_rows[0]
    front = ["id", "문법 유닛명", "카드 초록", "유형", "메모"]
    filled = ["판단", "패턴 학습 포인트"]
    rest = [h for h in head if h not in front + filled]
    byp = {}
    for j in judged: byp.setdefault(j["parent"], []).append(j)
    rows = []
    for r in concern_rows[1:]:
        d = dict(zip(head, r)); js = byp.get(d["id"].strip(), [])
        if len(js) > 1:
            jud = "나눔 → " + " / ".join(j["id"] for j in js)
            point = "\n".join(f"{j['id']} {j['form']}: {j['anc'] or j['why']}" for j in js)
        elif js:
            jud = f"패턴화 {js[0]['pat']}"; point = js[0]["anc"] if js[0]["pat"] == "가능" else js[0]["why"]
        else:
            jud = point = ""
        rows.append([d[h] for h in front] + [jud, point] + [d[h] for h in rest])
    def concern_style(ws, r, row):
        for c in (6, 7): ws.cell(r, c).fill = fill(GREEN)
        ws.cell(r, 6).font = F(bold=True, color="2C7A47" if "가능" in row[5] else "A85A12" if "나눔" in row[5] else "B0603A")
    table(ws, [("원본 (고민 목록 그대로)", GRAY, front), ("채움 — 원본의 빈 열", GREEN, filled), ("원본 (나머지 열, 순서 그대로)", GRAY, rest)],
          [9, 18, 22, 16, 18, 20, 34] + [12] * 4 + [26] * (len(rest) - 4), rows, concern_style)

    # ── 읽는 법 ──
    R = readme
    R.column_dimensions["A"].width = 30; R.column_dimensions["B"].width = 16; R.column_dimensions["C"].width = 70
    line = [0]
    def put(a="", b=None, c="", style=None):
        line[0] += 1; r = line[0]
        R.cell(r, 1, a); R.cell(r, 2, b); R.cell(r, 3, c)
        for k in (1, 2, 3): R.cell(r, k).font = F(); R.cell(r, k).alignment = Alignment(wrap_text=True, vertical="top")
        if style == "title": R.cell(r, 1).font = F(bold=True, size=14)
        if style == "h": R.cell(r, 1).font = F(bold=True, size=11, color="2F5E9E")
        if style in (GRAY, ORANGE, BLUE, GREEN, PURPLE):
            R.cell(r, 1).fill = fill(style); R.cell(r, 1).font = F(bold=True, color=DARK[style])
        return r
    n_src_rows = sum(len(u["sents"]) for u in units.values())
    put("유닛 정리 — 원본과 바꾼 것", style="title")
    put()
    put("원래 데이터", style="h")
    put("확정 CSV", None, "유기적 통합모드 문장 (공유용) - 문장1 변형후보 추가 (검토중)-문장만 확정.csv")
    r = put("  원본 유닛 수", len(units), "확정 CSV 의 id 행 수 (원본에서 센 값)")
    put("  원본 문장 수", n_src_rows, "확정 CSV 의 sentence 행 수 (원본에서 센 값)")
    put("고민 목록", None, "패턴화 고민 목록 - 목록.csv — 133유닛, '패턴 학습 포인트'·'판단' 열이 비어 있던 것")
    put()
    put("색", style="h")
    put("원본", None, "확정 CSV·고민 목록에 있던 값 그대로. 문장·번역·괄호·태그는 하나도 바꾸지 않았다", style=GRAY)
    put("변경 제안", None, "원본을 이렇게 바꾸자는 제안 — 나눈 유닛의 새 id · 새 카드 초록 · 새 뜻 · S1 지정뿐", style=ORANGE)
    put("추가", None, "원본에 없던 판정 — 유형 · 패턴화 가능/불가 · 공통 고정어 · 이유 · 메모", style=BLUE)
    put("채움", None, "고민 목록에 빈 열로 있던 '판단' · '패턴 학습 포인트'를 채운 것", style=GREEN)
    put("새로 씀", None, "나눈 유닛의 빈 칸을 채우려고 새로 쓴 학습 문장 — '나눈 유닛 문장' 탭", style=PURPLE)
    put()
    put("바꾼 것 (변경 제안)", style="h")
    put("  나눈 원본 유닛", "=COUNTA('나눈 유닛'!A3:A1000)", "한 유닛에 뜻·쓰임이 다른 갈래가 섞인 것(stop -ing / stop to 등)과 카드에 틀이 둘 적힌 것")
    put("  → 새 유닛", "=COUNTA('나눈 유닛'!G3:G1000)", "원본 id + 알파벳(10369-A …). 원래 S1 이 든 갈래가 A")
    put("  새 유닛의 학습 문장", "=COUNTA('나눈 유닛 문장'!E3:E2000)", "새 유닛마다 원래 구성과 같은 8칸(S1 · 문장1-2 · 문장1-3 · 기본 2 · 어려운 3)")
    put("    그중 기존 문장", "=COUNTIF('나눈 유닛 문장'!G3:G2000,\"기존\")", "원래 유닛의 문장을 문구 그대로 원래 칸에 넣은 것")
    put("    그중 새로 쓴 문장", "=COUNTIF('나눈 유닛 문장'!G3:G2000,\"새로 씀\")", "빈 칸만 새로 썼다 — 원본 5,371문장과 겹치지 않는다")
    put()
    put("판정 (추가)", style="h")
    put("  나눈 뒤 유닛", "=COUNTA('유닛별 판정'!A3:A2000)", "원본 유닛 - 나눈 원본 유닛 + 새 유닛")
    put("  패턴화 가능", "=COUNTIF('유닛별 판정'!G3:G2000,\"가능\")", "모든 문장에 같은 고정어가 있다 — 공통 패턴 찾기로 배울 수 있다")
    put("  패턴화 불가", "=COUNTIF('유닛별 판정'!G3:G2000,\"불가\")", "공통 규칙만 있다(형태 · 자리 · 어순 · 일치) 또는 같은 자리에 다른 낱말(열린 목록)")
    put("  고정어가 기능어 하나뿐", "=COUNTA('유닛별 판정'!I3:I2000)", "가능이지만 to · of 같은 낱말 하나뿐 — '확인' 열")
    put()
    put("고민 목록 (채움)", style="h")
    put("  패턴화 가능", "=COUNTIF('고민 목록 판단'!F3:F1000,\"패턴화 가능\")")
    put("  패턴화 불가", "=COUNTIF('고민 목록 판단'!F3:F1000,\"패턴화 불가\")")
    put("  나눔", "=COUNTIF('고민 목록 판단'!F3:F1000,\"나눔*\")")
    put()
    put("탭", style="h")
    put("나눈 유닛", None, "나눈 원본 유닛마다 원본(왼쪽 회색) → 새 유닛(가운데 주황)을 옆으로 나란히. 굵은 선 = 원본 유닛 경계, 가는 선 = 새 유닛 경계. 새 태그 'S1 ← 기본'은 원래 기본 문장을 새 유닛의 S1 으로 세웠다는 뜻")
    put("나눈 유닛 문장", None, "새 유닛마다 8칸. 회색 = 원래 유닛의 기존 문장(원래 유닛 · 원래 칸을 함께 적음), 보라 = 빈 칸을 채우려고 새로 쓴 문장")
    put("유닛별 판정", None, "나눈 뒤 유닛 한 줄씩. 나눈 유닛은 새 유닛·카드 초록·뜻 칸이 주황(제안). 패턴화 열로 거르면 가능/불가만 볼 수 있다")
    put("고민 목록 판단", None, "원본 열 그대로에 채운 두 열(초록)을 앞으로 당겨 둠 — 열 순서만 옮겼고 값은 그대로")
    for row in R.iter_rows(min_row=1, max_row=line[0], min_col=2, max_col=2):
        for c in row: c.alignment = Alignment(horizontal="right", vertical="top"); c.font = F(bold=True)
    wb._sheets = [wb[n] for n in ("읽는 법", "나눈 유닛", "나눈 유닛 문장", "유닛별 판정", "고민 목록 판단")]
    wb.active = 0
    wb.save(OUT / XLSX)

def main():
    units = cu.load_units()
    gen = {g["id"]: g for g in json.load(open(cu.OUT, encoding="utf-8"))}
    missing = [k for k in SPLITS if k not in units]
    if missing: cu.die(f"SPLITS 의 유닛이 CSV 에 없다: {missing}")
    OUT.mkdir(parents=True, exist_ok=True)

    concern = {}
    if CONCERN.exists():
        rows = list(csv.reader(open(CONCERN, encoding="utf-8")))
        head = rows[0]; ix = {h: i for i, h in enumerate(head)}
        for r in rows[1:]: concern[r[ix["id"]].strip()] = dict(zip(head, r))
    else:
        print(f"고민 목록 없음: {CONCERN} — 판단 CSV 는 건너뛴다", file=sys.stderr)

    written = json.load(open(NEW_SENTS, encoding="utf-8"))
    # 원본 문장 행은 순서·내용을 그대로 두고, 바꾼 것(변경 ·)과 새로 붙인 것(추가 ·)은 오른쪽 열에만 적는다
    O = ["원본 · id", "원본 · trigger", "원본 · 카드 초록 (형태)", "원본 · 카드 회색 1행 (뜻)", "원본 · 카드 회색 2행 (설명)", "원본 · 태그", "원본 · sentence", "원본 · translation"]
    C = ["변경 · 요약", "변경 · 새 유닛", "변경 · 새 카드 초록 (제안)", "변경 · 새 뜻 (제안)", "변경 · 새 태그"]
    A = ["추가 · 유형", "추가 · 패턴화", "추가 · 공통 고정어", "추가 · 패턴화 불가 이유", "추가 · 확인", "추가 · 나누거나 남긴 이유", "추가 · 메모"]
    all_rows, split_rows, judged = [], [], []
    recs, blocks = [], []  # 엑셀용 — 유닛 한 줄씩 / 나눈 유닛의 원본 → 새 유닛 묶음
    for uid, u in units.items():
        g = gen[uid]
        head = [uid, u["trigger"], u["form"], u["mean"], u["desc"]]
        subj = "괄호가 주어까지 묶었다" if subj_in_bracket(u["sents"]) else ""
        if uid not in SPLITS:
            pat, anc, why_not, chk = judge(u["form"], u["sents"], g["type"], keep=KEEP.get(uid, ""))
            keep = f"나누지 않음 — {KEEP[uid]}" if uid in KEEP else ""
            judged.append(dict(id=uid, parent=uid, form=u["form"], pat=pat, anc=anc, why=why_not, chk=chk))
            recs.append(dict(orig=uid, new="", form=u["form"], mean=u["mean"], s1=u["sents"][0][1], typ=g["type"], pat=pat, anc=anc,
                             why=why_not, chk=chk, reason=keep, memo=subj, concern=concern.get(uid, {}).get("유형", "")))
            for n, (tag, en, kr) in enumerate(u["sents"]):
                first = n == 0
                all_rows.append((head if first else [""] * 5) + [tag, en, kr] + [""] * 5
                                + ([g["type"], pat, anc, why_not, chk, keep, subj] if first else [""] * 7))
            continue
        parts = split_unit(u, g)
        where = {}  # 원본 문장 번호 → (새 유닛, 그 유닛의 S1 인가)
        for p in parts:
            for k, s in enumerate(p["sents"]):
                where[next(i for i, x in enumerate(u["sents"]) if x is s)] = (p, k == 0)
        summary = f"{len(parts)}개로 나눔: " + " · ".join(p["id"] for p in parts)
        for n, (tag, en, kr) in enumerate(u["sents"]):
            p, is_s1 = where[n]
            new_tag = ("S1" if n == 0 else f"S1 (원래 {tag})") if is_s1 else ""
            indep = [s for s in p["sents"] if s[0] not in VARIANT]
            memo = []
            if p["new_s1"]: memo.append("S1 새로 지정 — 주어 변형 문장 없음")
            memo.append(f"원래 문장 {len(p['sents'])}개 + 새로 쓴 문장 {len(written.get(p['id'], []))}개 = 8칸")
            if is_s1:
                # 판정은 채운 8칸 전체로 낸다 — 원래 문장 한두 개로는 고정어가 우연히 맞는다
                full = [(slot, en, kr) for slot, en, kr, _, _ in full_set(p, written)]
                pat, anc, why_not, chk = judge(p["form"], full, side=p["side"])
                judged.append(dict(id=p["id"], parent=uid, form=p["form"], pat=pat, anc=anc, why=why_not, chk=chk))
                recs.append(dict(orig=uid, new=p["id"], form=p["form"], mean=p["mean"], s1=p["sents"][0][1], typ=f"{g['type']}에서 나눔", pat=pat,
                                 anc=anc, why=why_not, chk=chk, reason=f"나눔 — {p['why']}", memo=" · ".join(memo), concern=concern.get(uid, {}).get("유형", "")))
                add = [f"{g['type']}에서 나눔", pat, anc, why_not, chk, f"나눔 — {p['why']}", " · ".join(memo)]
            else:
                add = [""] * 7
            all_rows.append((head if n == 0 else [""] * 5) + [tag, en, kr]
                            + [summary if n == 0 else "", p["id"], p["form"] if is_s1 else "", p["mean"] if is_s1 else "", new_tag] + add)
        blocks.append((u, parts))
        for p in parts:
            indep = [s for s in p["sents"] if s[0] not in VARIANT]
            memo = []
            if p["new_s1"]: memo.append("S1 새로 지정 — 주어 변형 문장 없음")
            memo.append(f"원래 문장 {len(p['sents'])}개 + 새로 쓴 문장 {len(written.get(p['id'], []))}개 = 8칸")
            for k, (tag, en, kr) in enumerate(p["sents"]):
                first_of_unit = p is parts[0] and k == 0
                orig_s1 = p["sents"][k] is u["sents"][0]
                split_rows.append([uid if first_of_unit else "", u["form"] if first_of_unit else "", u["mean"] if first_of_unit else "", tag, en, kr,
                                   p["id"] if k == 0 else "", p["form"] if k == 0 else "", p["mean"] if k == 0 else "",
                                   ("S1" if orig_s1 else f"S1 (원래 {tag})") if k == 0 else "",
                                   p["why"] if k == 0 else "", " · ".join(memo) if k == 0 else ""])

    # 원본 열은 다시 짜 맞추지 않고 확정 CSV 의 같은 행에서 그대로 옮긴다 — 작업 표시(여기까지 10-06 업로드) 같은 칸도 남는다
    src = list(csv.reader(open(cu.SRC, encoding="utf-8")))
    sh = src[0]
    pick = [sh.index(n) for n in ("id", "trigger", "카드 초록 (형태)", "카드 회색 1행 (뜻)", "카드 회색 2행 (설명)", "태그", "sentence", "translation")]
    body = [r for r in src[1:] if r[sh.index("sentence")].strip()]
    if len(body) != len(all_rows): cu.die(f"원본 문장 행 수가 다르다: {len(body)} ≠ {len(all_rows)}")
    for row, r in zip(all_rows, body):
        if row[6] != r[pick[6]].strip(): cu.die(f"원본 행 순서가 어긋났다: {row[6]} ≠ {r[pick[6]]}")
        row[:8] = [r[i] for i in pick]

    w = lambda name: csv.writer(open(OUT / name, "w", encoding="utf-8", newline=""))
    t = w("units-after-split.gen.csv"); t.writerow(O + C + A); t.writerows(all_rows)
    t = w("unit-splits.gen.csv")
    t.writerow(["원본 · id", "원본 · 카드 초록 (형태)", "원본 · 카드 회색 1행 (뜻)", "원본 · 태그", "원본 · sentence", "원본 · translation",
                "변경 · 새 유닛", "변경 · 새 카드 초록 (제안)", "변경 · 새 뜻 (제안)", "변경 · 새 태그", "추가 · 나누는 이유", "추가 · 메모"])
    t.writerows(split_rows)

    if concern:
        byp = {}
        for j in judged: byp.setdefault(j["parent"], []).append(j)
        rows = list(csv.reader(open(CONCERN, encoding="utf-8")))
        head = rows[0]; ip, ij = head.index("패턴 학습 포인트"), head.index("판단")
        t = w("pattern-concern-list.judged.gen.csv")
        # 원본에 빈 열로 있던 두 칸만 채운다 — 나머지 열은 그대로
        t.writerow([("채움 · " if i in (ip, ij) else "원본 · ") + h for i, h in enumerate(head)])
        for r in rows[1:]:
            js = byp.get(r[0].strip(), [])
            if len(js) > 1:
                r[ij] = "나눔 → " + " / ".join(f"{j['id']} {j['form']}" for j in js)
                r[ip] = " / ".join(f"{j['id']}: {j['anc'] or j['why']}" for j in js)
            elif js:
                r[ij] = f"패턴화 {js[0]['pat']}"
                r[ip] = js[0]["anc"] if js[0]["pat"] == "가능" else js[0]["why"]
            t.writerow(r)

    t = w("unit-split-sentences.gen.csv")
    t.writerow(["새 유닛", "카드 초록 (제안)", "뜻 (제안)", "칸", "sentence", "translation", "출처", "원래 유닛 · 원래 칸"])
    n_new = 0
    for u, parts in blocks:
        for p in parts:
            for k, (slot, en, kr, src, orig) in enumerate(full_set(p, written)):
                n_new += src == "새로 씀"
                t.writerow([p["id"] if k == 0 else "", p["form"] if k == 0 else "", p["mean"] if k == 0 else "", slot, en, kr, src,
                            f"{u['id']} · {orig}" if src == "기존" else ""])
    print(f"나눈 유닛 학습 문장: {sum(len(ps) for _, ps in blocks) * len(SLOTS)}칸 = 기존 {sum(len(ps) for _, ps in blocks) * len(SLOTS) - n_new} + 새로 씀 {n_new}")
    if concern: write_xlsx(units, recs, blocks, list(csv.reader(open(CONCERN, encoding="utf-8"))), judged)
    cnt = Counter(j["pat"] for j in judged)
    print(f"원본 {len(units)}유닛 · {sum(len(u['sents']) for u in units.values())}문장 → 나눈 유닛 {len(SPLITS)}개(새 유닛 {sum(1 for j in judged if j['parent'] != j['id'])}개)"
          f" · 나눈 뒤 {len(judged)}유닛 (패턴화 가능 {cnt['가능']} · 불가 {cnt['불가']})")
    print("고정어가 기능어 하나뿐:", sum(1 for j in judged if j["chk"]))
    print("산출:", ", ".join(p.name for p in sorted(OUT.glob("*.gen.*"))))

if __name__ == "__main__":
    main()
