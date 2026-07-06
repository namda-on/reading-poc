import { useEffect, useState } from 'react';
import quizzes from '../data/quizzes.json';
import type { QuizMap } from '../data/quizTypes';
import { markSolved } from '../lib/progress';
import './Quiz.css';

const QUIZ = quizzes as unknown as QuizMap;

interface Opt {
  text: string;
  correct: boolean;
}

// 저작 데이터가 정답을 대부분 1번에 두어 위치로 답을 유추할 수 있으므로, 마운트 시 한 번 섞는다.
function shuffled(options: string[], answerIndex: number): Opt[] {
  const opts: Opt[] = options.map((text, i) => ({ text, correct: i === answerIndex }));
  for (let i = opts.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [opts[i], opts[j]] = [opts[j], opts[i]];
  }
  return opts;
}

export function Quiz({ topicSeq, onDone }: { topicSeq: number; onDone: () => void }) {
  const questions = QUIZ[topicSeq] ?? [];
  // 보기 순서는 마운트 시 한 번만 정해 리렌더에도 유지.
  const [shuffledOptions] = useState<Opt[][]>(() => questions.map((q) => shuffled(q.options, q.answerIndex)));
  const [picked, setPicked] = useState<(number | null)[]>(() => questions.map(() => null));

  const answeredAll = questions.length > 0 && picked.every((p) => p !== null);
  const correct = picked.filter((p, i) => p !== null && shuffledOptions[i][p].correct).length;

  // 모든 문항을 풀면 완료로 기록(정답 여부와 무관).
  useEffect(() => {
    if (answeredAll) markSolved(topicSeq);
  }, [answeredAll, topicSeq]);

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
          {shuffledOptions[qi].map((opt, oi) => {
            const chosen = picked[qi] === oi;
            const revealed = picked[qi] !== null;
            const cls = revealed ? (opt.correct ? 'correct' : chosen ? 'wrong' : '') : '';
            return (
              <button
                key={oi}
                className={`quiz-opt ${cls}`}
                disabled={picked[qi] !== null}
                onClick={() => setPicked((arr) => arr.map((v, i) => (i === qi ? oi : v)))}
              >
                {opt.text}
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
