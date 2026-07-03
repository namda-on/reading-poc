import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData } from './data/types';
import { StoryList } from './components/StoryList';
import { TopicList } from './components/TopicList';
import { ReadingSession } from './components/ReadingSession';
import { Quiz } from './components/Quiz';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'stories' | 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('stories');
  const [storySeq, setStorySeq] = useState<number | null>(null);
  const [topicSeq, setTopicSeq] = useState<number | null>(null);

  const story = DATA.stories.find((s) => s.courseSeq === storySeq) ?? null;
  const topic = story?.topics.find((t) => t.topicSeq === topicSeq) ?? null;

  return (
    <div className="app">
      {screen === 'stories' && (
        <StoryList
          onPick={(s) => {
            setStorySeq(s);
            setScreen('topics');
          }}
        />
      )}
      {screen === 'topics' && story && (
        <TopicList
          story={story}
          onPick={(t) => {
            setTopicSeq(t);
            setScreen('session');
          }}
          onBack={() => setScreen('stories')}
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
            <button className="icon-btn" onClick={() => setScreen('topics')} aria-label="목록">‹</button>
            <span className="topbar-title">{topic.title}</span>
            <button className="replay-btn" onClick={() => setScreen('session')}>🔁 다시 듣기</button>
          </header>
          <Quiz topicSeq={topic.topicSeq} onDone={() => setScreen('topics')} />
        </div>
      )}
    </div>
  );
}
