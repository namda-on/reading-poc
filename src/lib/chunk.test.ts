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
});

describe('chunkSentence', () => {
  it('unit 스위치', () => {
    expect(chunkSentence('I want to go', 'word').length).toBe(4);
    expect(chunkSentence('I want to go', 'chunk').length).toBeLessThan(4);
  });
});
