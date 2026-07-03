import type { Chunk } from '../lib/chunk';
import './DialogBubble.css';

export function DialogBubble({ name, avatar, chunks, visible }: {
  name: string;
  avatar: string;
  chunks: Chunk[];
  visible: Set<number>;
}) {
  return (
    <div className="msg">
      <div className="avatar-col">
        <div className="avatar">{avatar}</div>
        <div className="avatar-name">{name}</div>
      </div>
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
