import type { Story } from '../data/types';
import { getSolved } from '../lib/progress';

export function TopicList({ story, onPick, onBack }: {
  story: Story;
  onPick: (topicSeq: number) => void;
  onBack: () => void;
}) {
  // 제목이 주제를 노출해 문제가 쉬워지므로 Episode 번호만 보여준다.
  const solved = getSolved();
  return (
    <div className="topic-screen">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <span className="topbar-title">{story.title}</span>
      </header>
      <div className="topic-list">
        <ul>
          {story.topics.map((t, i) => (
            <li key={t.topicSeq}>
              <button onClick={() => onPick(t.topicSeq)}>
                <span className="ep">Episode {i + 1}</span>
                {solved.has(t.topicSeq) && <span className="ep-check" aria-label="완료">✓</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
