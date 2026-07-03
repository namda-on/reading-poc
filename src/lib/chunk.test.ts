import { describe, it, expect } from 'vitest';
import { tokenize, chunkByWord, chunkByRule, chunkSentence } from './chunk';

describe('tokenize', () => {
  it('문장부호를 앞 토큰에 붙여 보존', () => {
    expect(tokenize('Look at this!').map((t) => t.text)).toEqual(['Look', 'at', 'this!']);
  });
});

describe('chunkByWord', () => {
  it('단어 청크(문장부호 포함)', () => {
    expect(chunkByWord('I need a hotel.').map((c) => c.text)).toEqual(['I', 'need', 'a', 'hotel.']);
  });
});

describe('chunkByRule', () => {
  it('전치사·to부정사 앞에서 끊는다', () => {
    expect(chunkByRule('I want to go to Rome').map((c) => c.text)).toEqual(['I', 'want to go', 'to Rome']);
  });
  it('고정표현 a lot of 는 쪼개지 않는다', () => {
    expect(chunkByRule('There are a lot of people').map((c) => c.text)).toEqual(['There are', 'a lot of people']);
  });
  it('접속사 and 앞에서 끊는다 (문장부호 보존)', () => {
    expect(chunkByRule('Hobbyists and tech fans.').map((c) => c.text)).toEqual(['Hobbyists', 'and tech fans.']);
  });
  it('최대 청크 길이 초과 시 단어 경계에서 강제 분할', () => {
    // 규칙만: ["I need electronic parts","for a project."] → maxWords=2 로 재분할
    expect(chunkByRule('I need electronic parts for a project.', 2).map((c) => c.text)).toEqual([
      'I need',
      'electronic parts',
      'for a',
      'project.',
    ]);
  });
  it('문장 끝(.!?) 뒤에서 무조건 끊는다 (청크가 문장을 넘지 않음)', () => {
    expect(chunkByRule('Yes. I worked on it for months.').map((c) => c.text)).toEqual([
      'Yes.',
      'I worked',
      'on it',
      'for months.',
    ]);
  });
  it('트리거 없는 문장도 최대 길이로 쪼갠다', () => {
    expect(chunkByRule('Rome has many good restaurants.', 2).map((c) => c.text)).toEqual([
      'Rome has',
      'many good',
      'restaurants.',
    ]);
  });
});

describe('chunkSentence', () => {
  it('unit 스위치', () => {
    expect(chunkSentence('I want to go', 'word').length).toBe(4);
    expect(chunkSentence('I want to go', 'chunk').length).toBeLessThan(4);
  });
});
