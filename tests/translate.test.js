'use strict';

const { translate } = require('../src/skills/translate');

describe('translate skill', () => {
  test('returns original text when no provider is given (fallback)', async () => {
    const text = 'Hello, world!';
    const result = await translate(text, 'French');
    expect(result).toBe(text);
  });

  test('calls provider with prompt containing text and target language', async () => {
    const mockProvider = jest.fn().mockResolvedValue('Bonjour, le monde!');
    const text = 'Hello, world!';
    const result = await translate(text, 'French', mockProvider);

    expect(mockProvider).toHaveBeenCalledTimes(1);
    expect(mockProvider.mock.calls[0][0]).toContain(text);
    expect(mockProvider.mock.calls[0][0]).toContain('French');
    expect(result).toBe('Bonjour, le monde!');
  });

  test('throws on empty text', async () => {
    await expect(translate('', 'Spanish')).rejects.toThrow('non-empty string');
  });

  test('throws on empty targetLanguage', async () => {
    await expect(translate('Hello', '')).rejects.toThrow('non-empty string');
  });
});
