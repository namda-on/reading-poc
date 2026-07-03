import type { Chunk } from '../lib/chunk';
import './DialogBubble.css';

export function DialogBubble({ speaker, chunks, visible }: {
  speaker: 'A' | 'B';
  chunks: Chunk[];
  visible: Set<number>;
}) {
  return (
    <div className={`bubble-row ${speaker === 'A' ? 'right' : 'left'}`}>
      <div className="bubble">
        {chunks.map((c, i) => (
          <span key={i} className="chunk" style={{ opacity: visible.has(i) ? 1 : 0 }}>
            {c.text}{' '}
          </span>
        ))}
      </div>
    </div>
  );
}
