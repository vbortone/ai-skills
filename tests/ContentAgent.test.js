'use strict';

const { ContentAgent } = require('../src/agents/ContentAgent');

describe('ContentAgent', () => {
  const sampleText =
    'The product launch was a huge success. Customers are happy and sales are up.';

  test('analyse returns summary, label, and null translation by default', async () => {
    const agent = new ContentAgent();
    const result = await agent.analyse(sampleText);

    expect(result).toHaveProperty('summary');
    expect(result).toHaveProperty('label');
    expect(result.translation).toBeNull();
    expect(typeof result.summary).toBe('string');
    expect(typeof result.label).toBe('string');
  });

  test('analyse includes translation when targetLanguage is specified', async () => {
    const mockProvider = jest.fn().mockResolvedValue('translated text');
    const agent = new ContentAgent({ provider: mockProvider });
    const result = await agent.analyse(sampleText, { targetLanguage: 'Spanish' });

    expect(result.translation).toBe('translated text');
    expect(mockProvider).toHaveBeenCalled();
  });

  test('analyse uses custom labels', async () => {
    const agent = new ContentAgent();
    const result = await agent.analyse(sampleText, {
      labels: ['success', 'failure', 'pending'],
    });
    expect(['success', 'failure', 'pending']).toContain(result.label);
  });

  test('analyse uses the provider for all skills', async () => {
    const mockProvider = jest.fn().mockResolvedValue('mock result');
    const agent = new ContentAgent({ provider: mockProvider });
    await agent.analyse(sampleText, { labels: ['good', 'bad'] });

    // summarize + classify are called in parallel
    expect(mockProvider).toHaveBeenCalledTimes(2);
  });
});
