import type { Story } from '../data/types';

export function TopicList({ story, onPick, onBack }: {
  story: Story;
  onPick: (topicSeq: number) => void;
  onBack: () => void;
}) {
  return (
    <div className="topic-screen">
      <header className="topbar">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">‹</button>
        <span className="topbar-title">{story.title}</span>
      </header>
      <div className="topic-list">
        <ul>
          {story.topics.map((t) => (
            <li key={t.topicSeq}>
              <button onClick={() => onPick(t.topicSeq)}>
                {t.title} <span>· {t.partner}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
