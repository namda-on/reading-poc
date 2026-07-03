export interface QuizQuestion {
  question: string;
  options: string[];
  answerIndex: number;
  explanation: string;
}

export type QuizMap = Record<number, QuizQuestion[]>; // key = topicSeq
