import { useState } from 'react';
import quizzes from '../data/quizzes.json';
import type { QuizMap } from '../data/quizTypes';
import './Quiz.css';

const QUIZ = quizzes as unknown as QuizMap;

export function Quiz({ topicSeq, onDone }: { topicSeq: number; onDone: () => void }) {
  const questions = QUIZ[topicSeq] ?? [];
  const [picked, setPicked] = useState<(number | null)[]>(() => questions.map(() => null));

  const answeredAll = picked.every((p) => p !== null);
  const correct = picked.filter((p, i) => p === questions[i].answerIndex).length;

  if (questions.length === 0) {
    return (
      <div className="quiz">
        <p>이 토픽에는 아직 문제가 없습니다.</p>
        <button className="primary" onClick={onDone}>토픽 목록으로</button>
      </div>
    );
  }

  return (
    <div className="quiz">
      {questions.map((q, qi) => (
        <div key={qi} className="quiz-q">
          <p className="quiz-question">
            {qi + 1}. {q.question}
          </p>
          {q.options.map((opt, oi) => {
            const chosen = picked[qi] === oi;
            const revealed = picked[qi] !== null;
            const isAnswer = oi === q.answerIndex;
            const cls = revealed ? (isAnswer ? 'correct' : chosen ? 'wrong' : '') : '';
            return (
              <button
                key={oi}
                className={`quiz-opt ${cls}`}
                disabled={picked[qi] !== null}
                onClick={() => setPicked((arr) => arr.map((v, i) => (i === qi ? oi : v)))}
              >
                {opt}
              </button>
            );
          })}
          {picked[qi] !== null && <p className="quiz-explain">{q.explanation}</p>}
        </div>
      ))}
      {answeredAll && (
        <div className="quiz-result">
          <p>
            {questions.length}문제 중 {correct}개 정답
          </p>
          <button className="primary" onClick={onDone}>토픽 목록으로</button>
        </div>
      )}
    </div>
  );
}
