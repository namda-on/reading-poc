import { useState } from 'react';
import dialogs from './data/dialogs.json';
import type { DialogsData, Mode, QuizType } from './data/types';
import { StoryList } from './components/StoryList';
import { TopicList } from './components/TopicList';
import { SessionStart } from './components/SessionStart';
import { ReadingSession } from './components/ReadingSession';
import { ListeningSession } from './components/ListeningSession';
import { MarqueeSession } from './components/MarqueeSession';
import { FixedSession } from './components/FixedSession';
import { QuizSheet } from './components/QuizSheet';
import './App.css';

const DATA = dialogs as unknown as DialogsData;
type Screen = 'stories' | 'topics' | 'session' | 'quiz';

// 마지막에 고른 모드·문제 유형을 기억해 다음에 기본 선택으로 쓴다.
const MODE_KEY = 'reading-poc:mode';
const QUIZ_KEY = 'reading-poc:quizType';
const MODES: Mode[] = ['reading', 'listening', 'marquee', 'fixed'];
const QUIZ_TYPES: QuizType[] = ['comprehension', 'arrange', 'dictation'];
function loadPref<T extends string>(key: string, allowed: T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    if (v && (allowed as string[]).includes(v)) return v as T;
  } catch {
    // localStorage 사용 불가 환경은 무시.
  }
  return fallback;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('stories');
  const [storySeq, setStorySeq] = useState<number | null>(null);
  const [topicSeq, setTopicSeq] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>(() => loadPref(MODE_KEY, MODES, 'reading'));
  const [quizType, setQuizType] = useState<QuizType>(() => loadPref(QUIZ_KEY, QUIZ_TYPES, 'comprehension'));
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
          initialMode={mode}
          initialQuizType={quizType}
          onStart={(m, q) => {
            setMode(m);
            setQuizType(q);
            try {
              localStorage.setItem(MODE_KEY, m); // 마지막 모드 기억
              localStorage.setItem(QUIZ_KEY, q); // 마지막 문제 유형 기억
            } catch {
              // 무시
            }
            setSessionRun((r) => r + 1);
            setPlaying(true);
          }}
          onBack={() => setScreen('topics')}
        />
      )}
      {(screen === 'session' || screen === 'quiz') && topic && playing && (() => {
        const props = {
          topic,
          showQuestion: quizType === 'comprehension', // 이해 문제일 때만 상단에 질문 미리보기
          onFinish: () => setScreen('quiz'),
          onBack: () => {
            setPlaying(false);
            setScreen('topics');
          },
        };
        const key = `${mode}-${topic.topicSeq}-${sessionRun}`;
        if (mode === 'listening') return <ListeningSession key={key} {...props} />;
        if (mode === 'marquee') return <MarqueeSession key={key} {...props} />;
        if (mode === 'fixed') return <FixedSession key={key} {...props} />;
        return <ReadingSession key={key} {...props} />;
      })()}
      {screen === 'quiz' && topic && (
        <QuizSheet
          topic={topic}
          quizType={quizType}
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
