import type { Script } from '../data/types';

const wordCount = (s: Script) => s.english.trim().split(/\s+/).length;

// 배열·받아쓰기 문제에 쓸 '핵심 1문장'을 고른다.
// 너무 짧거나(인사 등) 너무 긴 문장을 피해, 3~9단어 범위에서 가장 긴 문장을 고른다.
export function pickKeyScript(scripts: Script[]): Script {
  const inRange = scripts.filter((s) => {
    const n = wordCount(s);
    return n >= 3 && n <= 9;
  });
  if (inRange.length) return inRange.reduce((a, b) => (wordCount(b) > wordCount(a) ? b : a));
  // 범위에 없으면 가장 짧은 문장(분량 최소화).
  return scripts.reduce((a, b) => (wordCount(b) < wordCount(a) ? b : a));
}
