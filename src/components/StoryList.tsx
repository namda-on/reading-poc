import dialogs from '../data/dialogs.json';
import type { DialogsData } from '../data/types';

const DATA = dialogs as unknown as DialogsData;
const EMOJI: Record<number, string> = { 25: '🍎', 17: '📈', 2: '✈️' };

export function StoryList({ onPick }: { onPick: (courseSeq: number) => void }) {
  return (
    <div className="story-list">
      <h1>
        리딩 모드
        <small>어떤 이야기로 훈련할까요?</small>
      </h1>
      <ul>
        {DATA.stories.map((s) => (
          <li key={s.courseSeq}>
            <button onClick={() => onPick(s.courseSeq)}>
              <span className="story-emoji">{EMOJI[s.courseSeq] ?? '📖'}</span>
              <span className="story-text">
                <span className="story-title">{s.title}</span>
                <span className="story-sub">{s.subtitle}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
