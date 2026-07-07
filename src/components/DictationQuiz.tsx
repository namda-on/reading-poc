import { useMemo, useRef, useState } from 'react';
import type { Topic } from '../data/types';
import { pickKeyScript } from '../lib/keySentence';
import { markSolved } from '../lib/progress';
import './Quiz.css';
import './ExerciseQuiz.css';

// 채점: 대소문자·문장부호·여분 공백을 무시하고 비교.
const normalize = (s: string) => s.toLowerCase().replace(/[^a-z0-9']+/g, ' ').trim().replace(/\s+/g, ' ');

// 오디오를 듣고 문장을 직접 타이핑한다.
export function DictationQuiz({ topic, onDone }: { topic: Topic; onDone: () => void }) {
  const key = useMemo(() => pickKeyScript(topic.scripts), [topic]);
  const [value, setValue] = useState('');
  const [checked, setChecked] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const correct = normalize(value) === normalize(key.english);
  const play = () => {
    const a = audioRef.current;
    if (a && key.audioUrl) {
      a.src = key.audioUrl;
      a.currentTime = 0;
      a.play().catch(() => {});
    }
  };
  const check = () => {
    setChecked(true);
    markSolved(topic.topicSeq);
  };

  return (
    <div className="quiz">
      <div className="quiz-q">
        <p className="ex-label">듣고 문장을 받아쓰세요</p>
        <p className="ex-korean">{key.translated}</p>

        <audio ref={audioRef} preload="auto" />
        {key.audioUrl && (
          <button type="button" className="ex-audio" onClick={play}>🔊 문장 듣기</button>
        )}

        <textarea
          className="ex-input"
          value={value}
          disabled={checked}
          rows={2}
          placeholder="영어 문장을 입력하세요"
          onChange={(e) => setValue(e.target.value)}
        />

        {!checked ? (
          <button className="primary ex-check" disabled={!value.trim()} onClick={check}>
            확인
          </button>
        ) : (
          <div className="ex-result">
            <p className={`quiz-explain ${correct ? 'ex-ok' : 'ex-no'}`}>
              {correct ? '정답이에요! 🎉' : '아쉬워요'}
            </p>
            <p className="ex-answer-text">정답: {key.english}</p>
            <button className="primary" onClick={onDone}>토픽 목록으로</button>
          </div>
        )}
      </div>
    </div>
  );
}
