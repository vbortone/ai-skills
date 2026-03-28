# ai-skills

Personal AI skills and agents library.

Skills are focused, composable capabilities (summarise, classify, translate).
Agents are higher-level orchestrators that combine multiple skills to complete
a task.

## Installation

```bash
npm install
```

## Usage

### Skills

Skills accept an optional `provider` function – an async function that calls
your preferred LLM API. When no provider is given a simple offline fallback is
used (useful for testing and local development).

```js
const { summarize, classify, translate } = require('./src');

// Summarise text
const summary = await summarize('The quick brown fox jumps over the lazy dog.');

// Classify text
const label = await classify('I love this product!', ['positive', 'negative', 'neutral']);

// Translate text (passthrough without a provider)
const translated = await translate('Hello, world!', 'French', myLLMProvider);
```

### Agents

#### ContentAgent

Analyses a piece of content by running summarise, classify, and optionally
translate in a single call.

```js
const { ContentAgent } = require('./src');

const agent = new ContentAgent({ provider: myLLMProvider });
const result = await agent.analyse(text, {
  labels: ['positive', 'negative', 'neutral'],
  targetLanguage: 'Spanish',  // optional
});
// result: { summary, label, translation }
```

#### ResearchAgent

Takes a list of text snippets, summarises each one, and combines them into a
research brief.

```js
const { ResearchAgent } = require('./src');

const agent = new ResearchAgent({ provider: myLLMProvider });
const result = await agent.compile(snippets, { targetLanguage: 'French' });
// result: { summaries, brief }
```

## LLM Provider

Pass any async function as the `provider` option. It receives a string prompt
and must return a string response. Example using the OpenAI SDK:

```js
const OpenAI = require('openai');
const client = new OpenAI();

async function myProvider(prompt) {
  const response = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
  });
  return response.choices[0].message.content;
}
```

## Tests

```bash
npm test
```

## License

MIT
