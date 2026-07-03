import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData } from './data/types';
import { TopicList } from './components/TopicList';
import { ReadingSession } from './components/ReadingSession';
import { Quiz } from './components/Quiz';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('topics');
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const topic = DATA.topics.find((t) => t.topicSeq === topicSeq) ?? null;

  return (
    <div className="app">
      {screen === 'topics' && (
        <TopicList
          onPick={(s) => {
            setTopicSeq(s);
            setScreen('session');
          }}
        />
      )}
      {screen === 'session' && topic && (
        <ReadingSession
          key={topic.topicSeq}
          topic={topic}
          onFinish={() => setScreen('quiz')}
          onBack={() => setScreen('topics')}
        />
      )}
      {screen === 'quiz' && topic && (
        <div className="quiz-screen">
          <header className="topbar">
            <button className="icon-btn" onClick={() => setScreen('session')} aria-label="뒤로">‹</button>
            <span className="topbar-title">{topic.title}</span>
          </header>
          <Quiz topicSeq={topic.topicSeq} onDone={() => setScreen('topics')} />
        </div>
      )}
    </div>
  );
}
