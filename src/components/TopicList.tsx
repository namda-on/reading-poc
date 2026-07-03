import dialogs from '../data/dialogs.json';
import type { DialogsData } from '../data/types';

const DATA = dialogs as unknown as DialogsData;

export function TopicList({ onPick }: { onPick: (topicSeq: number) => void }) {
  return (
    <div className="topic-list">
      <h1>
        {DATA.courseTitle} <small>(A2)</small>
      </h1>
      <ul>
        {DATA.topics.map((t) => (
          <li key={t.topicSeq}>
            <button onClick={() => onPick(t.topicSeq)}>
              {t.title} <span>· {t.partner}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
