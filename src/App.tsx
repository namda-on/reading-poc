import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData } from './data/types';
import { TopicList } from './components/TopicList';
import { ReadingSession } from './components/ReadingSession';
import { Quiz } from './components/Quiz';
import { SettingsPanel } from './components/SettingsPanel';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('topics');
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const topic = DATA.topics.find((t) => t.topicSeq === topicSeq) ?? null;

  return (
    <div className="app">
      {screen !== 'topics' && (
        <header className="app-header">
          <button onClick={() => setScreen('topics')}>← 목록</button>
          <SettingsPanel />
        </header>
      )}
      <main className="app-main">
        {screen === 'topics' && (
          <TopicList
            onPick={(s) => {
              setTopicSeq(s);
              setScreen('session');
            }}
          />
        )}
        {screen === 'session' && topic && (
          <ReadingSession key={topic.topicSeq} topic={topic} onFinish={() => setScreen('quiz')} />
        )}
        {screen === 'quiz' && topic && <Quiz topicSeq={topic.topicSeq} onDone={() => setScreen('topics')} />}
      </main>
    </div>
  );
}
