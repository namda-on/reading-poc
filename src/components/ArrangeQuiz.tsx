import { useMemo, useState } from 'react';
import type { Topic } from '../data/types';
import { pickKeyScript } from '../lib/keySentence';
import { markSolved } from '../lib/progress';
import './Quiz.css';
import './ExerciseQuiz.css';

interface Word {
  id: number;
  text: string;
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// 한국어 뜻을 주고, 뒤섞인 영어 단어를 순서대로 탭해 문장을 완성한다.
export function ArrangeQuiz({ topic, onDone }: { topic: Topic; onDone: () => void }) {
  const key = useMemo(() => pickKeyScript(topic.scripts), [topic]);
  const tokens = useMemo(() => key.english.trim().split(/\s+/), [key]);
  const [bank, setBank] = useState<Word[]>(() => shuffle(tokens.map((t, i) => ({ id: i, text: t }))));
  const [answer, setAnswer] = useState<Word[]>([]);
  const [checked, setChecked] = useState(false);

  const pick = (w: Word) => {
    if (checked) return;
    setBank((b) => b.filter((x) => x.id !== w.id));
    setAnswer((a) => [...a, w]);
  };
  const unpick = (w: Word) => {
    if (checked) return;
    setAnswer((a) => a.filter((x) => x.id !== w.id));
    setBank((b) => [...b, w]);
  };

  const correct = answer.map((w) => w.text).join(' ') === tokens.join(' ');
  const check = () => {
    setChecked(true);
    markSolved(topic.topicSeq);
  };

  return (
    <div className="quiz">
      <div className="quiz-q">
        <p className="ex-label">다음 뜻의 문장을 순서대로 완성하세요</p>
        <p className="ex-korean">{key.translated}</p>

        <div className={`ex-answer${checked ? (correct ? ' correct' : ' wrong') : ''}`}>
          {answer.length === 0 ? (
            <span className="ex-placeholder">단어를 순서대로 탭하세요</span>
          ) : (
            answer.map((w) => (
              <button key={w.id} className="ex-chip in-answer" onClick={() => unpick(w)}>
                {w.text}
              </button>
            ))
          )}
        </div>

        {bank.length > 0 && (
          <div className="ex-bank">
            {bank.map((w) => (
              <button key={w.id} className="ex-chip" onClick={() => pick(w)}>
                {w.text}
              </button>
            ))}
          </div>
        )}

        {!checked ? (
          <button className="primary ex-check" disabled={bank.length > 0} onClick={check}>
            확인
          </button>
        ) : (
          <div className="ex-result">
            <p className="quiz-explain">{correct ? '정답이에요! 🎉' : `정답: ${tokens.join(' ')}`}</p>
            <button className="primary" onClick={onDone}>토픽 목록으로</button>
          </div>
        )}
      </div>
    </div>
  );
}
