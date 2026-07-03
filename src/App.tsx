import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData } from './data/types';
import { StoryList } from './components/StoryList';
import { TopicList } from './components/TopicList';
import { ReadingSession } from './components/ReadingSession';
import { QuizSheet } from './components/QuizSheet';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'stories' | 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('stories');
  const [storySeq, setStorySeq] = useState<number | null>(null);
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const [sessionRun, setSessionRun] = useState(0); // 다시 듣기 시 세션 리마운트용
  const [autoStart, setAutoStart] = useState(false); // 다시 듣기면 시작 버튼 없이 바로 재생

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
            setAutoStart(false);
            setScreen('session');
          }}
          onBack={() => setScreen('stories')}
        />
      )}
      {(screen === 'session' || screen === 'quiz') && topic && (
        <ReadingSession
          key={`${topic.topicSeq}-${sessionRun}`}
          topic={topic}
          autoStart={autoStart}
          onFinish={() => setScreen('quiz')}
          onBack={() => setScreen('topics')}
        />
      )}
      {screen === 'quiz' && topic && (
        <QuizSheet
          topicSeq={topic.topicSeq}
          onReplay={() => {
            setAutoStart(true); // 다시 듣기는 바로 재생
            setSessionRun((r) => r + 1); // 세션 리마운트 → 처음부터
            setScreen('session');
          }}
          onClose={() => setScreen('topics')}
        />
      )}
    </div>
  );
}
