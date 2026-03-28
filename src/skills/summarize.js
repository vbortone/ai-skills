'use strict';

/**
 * Summarize skill – condenses a block of text into a shorter summary.
 *
 * In a real deployment this would call an LLM API (e.g. OpenAI, Anthropic).
 * The `provider` parameter is expected to be an async function with the
 * signature:  provider(prompt: string) => Promise<string>
 *
 * A default provider is included for use in tests and local development; it
 * extracts the first sentence as a minimal fallback summary.
 */

/**
 * @param {string} text - The text to summarize.
 * @param {Function} [provider] - Optional LLM provider function.
 * @returns {Promise<string>} The summary.
 */
async function summarize(text, provider) {
  if (typeof text !== 'string' || text.trim() === '') {
    throw new Error('summarize: text must be a non-empty string');
  }

  if (provider) {
    const prompt = `Summarize the following text in one or two sentences:\n\n${text}`;
    return provider(prompt);
  }

  // Fallback: return the first sentence.
  const firstSentence = text.split(/[.!?]/)[0].trim();
  return firstSentence || text;
}

module.exports = { summarize };
