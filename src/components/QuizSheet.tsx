import { Quiz } from './Quiz';
import './QuizSheet.css';

export function QuizSheet({ topicSeq, onReplay, onClose }: {
  topicSeq: number;
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
          <Quiz topicSeq={topicSeq} onDone={onClose} />
        </div>
      </div>
    </>
  );
}
