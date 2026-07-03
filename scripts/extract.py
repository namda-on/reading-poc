"""server.sqlite 에서 여러 스토리(코스)의 A2(level 2) 대화를 추출해
src/data/dialogs.json 으로 굽는다. 각 토픽은 도입부 6턴만 사용(대화당 1문항)."""
import sqlite3, json, os

SQLITE = "/Users/namda/sayvoca/conversation-agent/server.sqlite"
LEVEL = 2
MAX_SCRIPTS = 6  # 리딩 모드 분량: 자연스러운 도입부 6턴만
# 포함할 스토리(코스). 표시 순서대로.
INCLUDE = [25, 17, 2]
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "dialogs.json")


def words_from_taglist(en, tag_list):
    words = []
    for t in tag_list or []:
        s, e = t.get("s"), t.get("e")
        if s is None or e is None:
            continue
        words.append({"text": en[s:e], "start": s, "end": e})
    return words


def build_topic(c, t):
    topic_seq = t["sq"]
    dseq = topic_seq * 10 + LEVEL
    lo, hi = dseq * 100, dseq * 100 + 99
    rows = c.execute(
        "SELECT seq,data FROM ConversationDialogScriptKR WHERE seq BETWEEN ? AND ? ORDER BY seq",
        (lo, hi)).fetchall()
    scripts = []
    for seq, data in rows:
        d = json.loads(data)
        scripts.append({
            "seq": seq,
            "speaker": d["p"],
            "english": d["en"],
            "translated": d.get("tr", ""),
            "hint": d.get("hint"),
            "words": words_from_taglist(d["en"], d.get("tagList")),
        })
    return {"topicSeq": topic_seq, "title": t["t"], "partner": t["c"], "scripts": scripts[:MAX_SCRIPTS]}


def main():
    c = sqlite3.connect(SQLITE)
    raw = json.loads(c.execute(
        "SELECT content FROM ResourceFileKR WHERE name='ConversationCourses'").fetchone()[0])
    courses = {co["sq"]: co for co in raw}

    stories = []
    for course_seq in INCLUDE:
        co = courses[course_seq]
        topics = [build_topic(c, t) for t in co["to"]]
        topics = [tp for tp in topics if tp["scripts"]]
        stories.append({"courseSeq": course_seq, "title": co["t"], "subtitle": co.get("d", ""), "topics": topics})

    out = {"level": LEVEL, "stories": stories}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(stories)} stories, {sum(len(s['topics']) for s in stories)} topics -> {OUT}")


if __name__ == "__main__":
    main()
