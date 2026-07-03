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
          <span key={i} className="chunk" style={{ visibility: visible.has(i) ? 'visible' : 'hidden' }}>
            {c.text}{' '}
          </span>
        ))}
      </div>
    </div>
  );
}
