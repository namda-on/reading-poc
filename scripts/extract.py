"""server.sqlite 에서 스티브 잡스(course 25) A2(level 2) 대화 22개를 추출해
src/data/dialogs.json 으로 굽는다. 일회성이지만 재생성 가능하도록 커밋한다."""
import sqlite3, json, os

SQLITE = "/Users/namda/sayvoca/conversation-agent/server.sqlite"
COURSE_SEQ = 25
LEVEL = 2
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "data", "dialogs.json")


def words_from_taglist(en, tag_list):
    words = []
    for t in tag_list or []:
        s, e = t.get("s"), t.get("e")
        if s is None or e is None:
            continue
        words.append({"text": en[s:e], "start": s, "end": e})
    return words


def main():
    c = sqlite3.connect(SQLITE)
    raw = json.loads(c.execute(
        "SELECT content FROM ResourceFileKR WHERE name='ConversationCourses'").fetchone()[0])
    course = next((co for co in raw if co["sq"] == COURSE_SEQ), None)
    assert course, "course 25 not found"

    topics = []
    for t in course["to"]:
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
        if scripts:
            topics.append({"topicSeq": topic_seq, "title": t["t"], "partner": t["c"], "scripts": scripts})

    out = {"courseSeq": COURSE_SEQ, "courseTitle": course["t"], "level": LEVEL, "topics": topics}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(topics)} topics -> {OUT}")


if __name__ == "__main__":
    main()
