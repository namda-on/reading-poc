import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData, Mode } from './data/types';
import { StoryList } from './components/StoryList';
import { TopicList } from './components/TopicList';
import { SessionStart } from './components/SessionStart';
import { ReadingSession } from './components/ReadingSession';
import { ListeningSession } from './components/ListeningSession';
import { MarqueeSession } from './components/MarqueeSession';
import { QuizSheet } from './components/QuizSheet';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'stories' | 'topics' | 'session' | 'quiz';

export default function App() {
  const [screen, setScreen] = useState<Screen>('stories');
  const [storySeq, setStorySeq] = useState<number | null>(null);
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>('reading');
  const [playing, setPlaying] = useState(false); // 시작 화면(false) → 재생(true)
  const [sessionRun, setSessionRun] = useState(0); // 다시 듣기 시 세션 리마운트용

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
            setPlaying(false); // 토픽 진입 시 시작 화면(모드 선택)부터
            setScreen('session');
          }}
          onBack={() => setScreen('stories')}
        />
      )}
      {screen === 'session' && topic && !playing && (
        <SessionStart
          topic={topic}
          onStart={(m) => {
            setMode(m);
            setSessionRun((r) => r + 1);
            setPlaying(true);
          }}
          onBack={() => setScreen('topics')}
        />
      )}
      {(screen === 'session' || screen === 'quiz') && topic && playing && (() => {
        const props = {
          topic,
          onFinish: () => setScreen('quiz'),
          onBack: () => {
            setPlaying(false);
            setScreen('topics');
          },
        };
        const key = `${mode}-${topic.topicSeq}-${sessionRun}`;
        if (mode === 'listening') return <ListeningSession key={key} {...props} />;
        if (mode === 'marquee') return <MarqueeSession key={key} {...props} />;
        return <ReadingSession key={key} {...props} />;
      })()}
      {screen === 'quiz' && topic && (
        <QuizSheet
          topicSeq={topic.topicSeq}
          onReplay={() => {
            setSessionRun((r) => r + 1); // 세션 리마운트 → 처음부터, 같은 모드로 즉시 재생
            setScreen('session');
          }}
          onClose={() => {
            setPlaying(false);
            setScreen('topics');
          }}
        />
      )}
    </div>
  );
}
