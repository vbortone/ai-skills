'use strict';

const { classify } = require('../src/skills/classify');

describe('classify skill', () => {
  const labels = ['positive', 'negative', 'neutral'];

  test('picks label based on keyword frequency (fallback)', async () => {
    const text = 'This is a positive experience. Everything is positive and great.';
    const result = await classify(text, labels);
    expect(result).toBe('positive');
  });

  test('defaults to first label when no keyword matches', async () => {
    const text = 'Random words with no matches here.';
    const result = await classify(text, labels);
    expect(result).toBe('positive');
  });

  test('calls provider with prompt containing text and labels', async () => {
    const mockProvider = jest.fn().mockResolvedValue('negative');
    const text = 'This was a terrible experience.';
    const result = await classify(text, labels, mockProvider);

    expect(mockProvider).toHaveBeenCalledTimes(1);
    expect(mockProvider.mock.calls[0][0]).toContain(text);
    expect(result).toBe('negative');
  });

  test('throws on empty text', async () => {
    await expect(classify('', labels)).rejects.toThrow('non-empty string');
  });

  test('throws on empty labels array', async () => {
    await expect(classify('Some text', [])).rejects.toThrow('non-empty array');
  });
});
