// 푼 토픽(topicSeq) 집합을 localStorage 에 저장. 목록에서 ✓ 표시에 사용.
const KEY = 'reading-poc:solved';

export function getSolved(): Set<number> {
  try {
    return new Set(JSON.parse(localStorage.getItem(KEY) || '[]') as number[]);
  } catch {
    return new Set();
  }
}

export function markSolved(topicSeq: number): void {
  try {
    const s = getSolved();
    s.add(topicSeq);
    localStorage.setItem(KEY, JSON.stringify([...s]));
  } catch {
    // localStorage 사용 불가 환경은 무시
  }
}
