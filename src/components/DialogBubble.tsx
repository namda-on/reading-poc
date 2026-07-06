import type { Chunk } from '../lib/chunk';
import './DialogBubble.css';

const FADE_IN = 'opacity 450ms ease';
const FADE_OUT = 'opacity 250ms ease'; // 사라짐은 더 빠르게(꼬리가 차례대로 산뜻하게 빠지도록)

export function DialogBubble({ name, avatar, chunks, visible, fadeIn = true, fadeOut = true }: {
  name: string;
  avatar: string;
  chunks: Chunk[];
  visible: Set<number>;
  fadeIn?: boolean; // false 면 등장 시 즉시 나타남
  fadeOut?: boolean; // false 면 사라질 때 즉시 사라짐
}) {
  return (
    <div className="msg">
      <div className="avatar-col">
        <div className="avatar">{avatar}</div>
        <div className="avatar-name">{name}</div>
      </div>
      <div className="bubble">
        {chunks.map((c, i) => {
          const on = visible.has(i);
          // 값이 바뀌는 순간의 transition 이 방향(등장/사라짐)을 결정한다.
          const transition = on ? (fadeIn ? FADE_IN : 'none') : (fadeOut ? FADE_OUT : 'none');
          return (
            <span key={i} className="chunk" style={{ opacity: on ? 1 : 0, transition }}>
              {c.text}{' '}
            </span>
          );
        })}
      </div>
    </div>
  );
}
