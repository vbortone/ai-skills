'use strict';

const { ResearchAgent } = require('../src/agents/ResearchAgent');

describe('ResearchAgent', () => {
  const snippets = [
    'The ocean covers more than 70% of the Earth surface.',
    'Coral reefs support around 25% of all marine species.',
  ];

  test('compile returns summaries array and brief string', async () => {
    const agent = new ResearchAgent();
    const result = await agent.compile(snippets);

    expect(result).toHaveProperty('summaries');
    expect(result).toHaveProperty('brief');
    expect(Array.isArray(result.summaries)).toBe(true);
    expect(result.summaries).toHaveLength(2);
    expect(typeof result.brief).toBe('string');
  });

  test('brief is the concatenation of summaries by default', async () => {
    const agent = new ResearchAgent();
    const result = await agent.compile(snippets);

    expect(result.brief).toBe(result.summaries.join(' '));
  });

  test('translates the brief when targetLanguage is specified', async () => {
    const mockProvider = jest.fn().mockResolvedValue('translated brief');
    const agent = new ResearchAgent({ provider: mockProvider });
    const result = await agent.compile(snippets, { targetLanguage: 'German' });

    expect(result.brief).toBe('translated brief');
  });

  test('throws when snippets array is empty', async () => {
    const agent = new ResearchAgent();
    await expect(agent.compile([])).rejects.toThrow('non-empty array');
  });

  test('throws when snippets is not an array', async () => {
    const agent = new ResearchAgent();
    await expect(agent.compile('not an array')).rejects.toThrow('non-empty array');
  });
});
