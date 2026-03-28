'use strict';

const { summarize } = require('../src/skills/summarize');

describe('summarize skill', () => {
  test('returns first sentence as fallback summary', async () => {
    const text = 'The sky is blue. Stars are bright. The moon glows.';
    const result = await summarize(text);
    expect(result).toBe('The sky is blue');
  });

  test('calls provider with a prompt containing the text', async () => {
    const mockProvider = jest.fn().mockResolvedValue('Mock summary');
    const text = 'Some interesting text.';
    const result = await summarize(text, mockProvider);

    expect(mockProvider).toHaveBeenCalledTimes(1);
    expect(mockProvider.mock.calls[0][0]).toContain(text);
    expect(result).toBe('Mock summary');
  });

  test('throws on empty text', async () => {
    await expect(summarize('')).rejects.toThrow('non-empty string');
  });

  test('throws on non-string input', async () => {
    await expect(summarize(42)).rejects.toThrow('non-empty string');
  });
});
