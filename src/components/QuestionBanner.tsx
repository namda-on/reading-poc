import quizzes from '../data/quizzes.json';
import type { QuizMap } from '../data/quizTypes';
import './QuestionBanner.css';

const QUIZ = quizzes as unknown as QuizMap;

// 세션 내내 상단에 문제를 노출해, 무엇을 들으며 찾아야 하는지 미리 알려준다(선택지는 끝난 뒤 퀴즈에서).
export function QuestionBanner({ topicSeq }: { topicSeq: number }) {
  const questions = QUIZ[topicSeq] ?? [];
  if (questions.length === 0) return null;
  return (
    <div className="question-banner">
      <span className="qb-tag">문제</span>
      <div className="qb-list">
        {questions.map((q, i) => (
          <p key={i}>{q.question}</p>
        ))}
      </div>
    </div>
  );
}
