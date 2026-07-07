import quizzes from '../data/quizzes.json';
import type { QuizMap } from '../data/quizTypes';

const QUIZ = quizzes as unknown as QuizMap;

// 핵심 문장 선정용 힌트: 해당 토픽 퀴즈의 질문·정답·해설을 합친 한국어 텍스트.
export function quizHintFor(topicSeq: number): string {
  const q = (QUIZ[topicSeq] ?? [])[0];
  if (!q) return '';
  const answer = q.options[q.answerIndex] ?? '';
  return [q.question, answer, q.explanation].filter(Boolean).join(' ');
}
