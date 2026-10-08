"""확정 CSV의 901유닛을 기획 검토용으로 정리한다 — ① 한 유닛에 갈래가 섞인 것을 나누고 ② 나눈 뒤 유닛마다 패턴화 가능/불가를 판정한다.
소스(레포 밖): UNITS_CSV(classify_units.py 와 같은 확정 CSV) · CONCERN_CSV(기본 ~/Downloads/패턴화 고민 목록 - 목록.csv)
산출: public/units/ 아래 CSV 세 장 — 배포 사이트에서 서빙되므로 Google 시트가 IMPORTDATA 로 바로 불러온다(BOM 을 붙이면 첫 칸에 섞여 들어간다)
  unit-splits.gen.csv            나눌 유닛 — 새 유닛마다 카드 초록·뜻 제안과 배정된 문장(문장 한 줄 = 한 행, 확정 CSV 와 같은 모양)
  units-after-split.gen.csv      나눈 뒤 전체 유닛 — 패턴화 가능/불가와 그 근거
  pattern-concern-list.judged.gen.csv  고민 목록 133유닛에 '패턴 학습 포인트'·'판단'을 채운 것

나누는 기준: 갈래마다 뜻이나 쓰는 자리가 달라 따로 골라야 하는 것(stop -ing / stop to, some / any, at / on / in …)과
카드 초록에 틀이 둘 적힌 것. 같은 자리에 같은 부류 낱말이 갈아 끼워지는 열린 목록(의문사·감각동사·접속사),
주어에 맞춰 정해지는 것(myself / yourself, 부가의문문), 뉘앙스 차이(can / could)는 나누지 않는다 — KEEP 에 이유를 적는다.
"""
import csv, os, re, sys
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

def main():
    units = cu.load_units()
    gen = {g["id"]: g for g in __import__("json").load(open(cu.OUT, encoding="utf-8"))}
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

    # ① 나눌 유닛
    split_rows, after = [], []
    for uid, u in units.items():
        g = gen[uid]
        if uid in SPLITS:
            parts = split_unit(u, g)
            for p in parts:
                indep = [s for s in p["sents"] if s[0] not in VARIANT]
                short = max(0, 3 - len(indep))
                memo = []
                if p["new_s1"]: memo.append(f"S1 새로 지정({p['sents'][0][1]}) — 주어 변형 문장 없음")
                if short: memo.append(f"독립 문장 {len(indep)}개 — {short}개 보강 필요(S1 + 2문장 기준)")
                for n, (tag, en, kr) in enumerate(p["sents"]):
                    split_rows.append([uid if n == 0 else "", p["id"] if n == 0 else "", p["side"] if n == 0 else "", p["why"] if n == 0 else "",
                                       p["form"] if n == 0 else "", p["mean"] if n == 0 else "", "S1" if n == 0 else tag, en, kr, " · ".join(memo) if n == 0 else ""])
                pat, anc, why_not, chk = judge(p["form"], p["sents"], side=p["side"])
                after.append([p["id"], uid, "분리", p["form"], p["mean"], f"{g['type']} → 분리", pat, anc, why_not, chk, len(indep), "",
                              "Y" if subj_in_bracket(p["sents"]) else "", concern.get(uid, {}).get("유형", ""), concern.get(uid, {}).get("메모", "")])
            continue
        indep = [s for s in u["sents"] if s[0] not in VARIANT]
        pat, anc, why_not, chk = judge(u["form"], u["sents"], g["type"], keep=KEEP.get(uid, ""))
        after.append([uid, uid, "", u["form"], u["mean"], g["type"], pat, anc, why_not, chk, len(indep), KEEP.get(uid, ""),
                      "Y" if subj_in_bracket(u["sents"]) else "", concern.get(uid, {}).get("유형", ""), concern.get(uid, {}).get("메모", "")])

    w = lambda name: csv.writer(open(OUT / name, "w", encoding="utf-8", newline=""))
    s = w("unit-splits.gen.csv")
    s.writerow(["원 유닛", "새 유닛", "갈래", "나누는 이유", "카드 초록 (제안)", "카드 회색 1행 (뜻, 제안)", "태그", "sentence", "translation", "메모"])
    s.writerows(split_rows)
    a = w("units-after-split.gen.csv")
    a.writerow(["유닛", "원 유닛", "분리", "카드 초록", "카드 회색 1행 (뜻)", "기존 분류", "패턴화", "공통 고정어", "패턴화 불가 이유",
                "확인", "독립 문장 수", "대비형인데 나누지 않은 이유", "괄호에 주어 포함", "고민 목록 유형", "고민 목록 메모"])
    a.writerows(after)

    if concern:
        byp = {}
        for r in after: byp.setdefault(r[1], []).append(r)
        rows = list(csv.reader(open(CONCERN, encoding="utf-8")))
        head = rows[0]; ip, ij = head.index("패턴 학습 포인트"), head.index("판단")
        c = w("pattern-concern-list.judged.gen.csv"); c.writerow(head)
        for r in rows[1:]:
            rs = byp.get(r[0].strip(), [])
            if len(rs) > 1:
                r[ij] = "분리 필요 → " + " / ".join(f"{x[0]} {x[3]}" for x in rs)
                r[ip] = " / ".join(f"{x[0]}: {x[7] or x[8]}" for x in rs)
            elif rs:
                x = rs[0]
                r[ij] = f"패턴화 {x[6]}"
                r[ip] = x[7] if x[6] == "가능" else x[8]
            c.writerow(r)

    n_split = sum(1 for r in after if r[2] == "분리")
    cnt = Counter(r[6] for r in after)
    print(f"나눌 유닛 {len(SPLITS)}개 → 새 유닛 {n_split}개 · 나눈 뒤 전체 {len(after)}유닛 (패턴화 가능 {cnt['가능']} · 불가 {cnt['불가']})")
    print("보강이 필요한 새 유닛:", sum(1 for r in after if r[2] == "분리" and r[10] < 3), "· 고정어가 기능어 하나뿐:", sum(1 for r in after if r[9]))
    print("산출:", ", ".join(p.name for p in sorted(OUT.glob("*.gen.csv"))))

if __name__ == "__main__":
    main()
