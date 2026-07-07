import type { QuizType, Topic } from '../data/types';
import { Quiz } from './Quiz';
import { ArrangeQuiz } from './ArrangeQuiz';
import { DictationQuiz } from './DictationQuiz';
import './QuizSheet.css';

export function QuizSheet({ topic, quizType, onReplay, onClose }: {
  topic: Topic;
  quizType: QuizType;
  onReplay: () => void;
  onClose: () => void;
}) {
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="문제">
        <div className="sheet-handle" />
        <div className="sheet-head">
          <span className="sheet-title">문제</span>
          <button className="sheet-replay" onClick={onReplay}>🔁 다시 듣기</button>
        </div>
        <div className="sheet-body">
          {quizType === 'arrange' ? (
            <ArrangeQuiz topic={topic} onDone={onClose} />
          ) : quizType === 'dictation' ? (
            <DictationQuiz topic={topic} onDone={onClose} />
          ) : (
            <Quiz topicSeq={topic.topicSeq} onDone={onClose} />
          )}
        </div>
      </div>
    </>
  );
}
