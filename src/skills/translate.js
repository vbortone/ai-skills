'use strict';

/**
 * Translate skill – translates text from one language to another.
 *
 * The `provider` parameter is expected to be an async function with the
 * signature:  provider(prompt: string) => Promise<string>
 *
 * A passthrough fallback is included so the module can be used without a
 * live LLM API (useful in tests and local development).
 */

/**
 * @param {string} text - The text to translate.
 * @param {string} targetLanguage - The target language (e.g. "French").
 * @param {Function} [provider] - Optional LLM provider function.
 * @returns {Promise<string>} The translated text.
 */
async function translate(text, targetLanguage, provider) {
  if (typeof text !== 'string' || text.trim() === '') {
    throw new Error('translate: text must be a non-empty string');
  }
  if (typeof targetLanguage !== 'string' || targetLanguage.trim() === '') {
    throw new Error('translate: targetLanguage must be a non-empty string');
  }

  if (provider) {
    const prompt = `Translate the following text to ${targetLanguage}:\n\n${text}`;
    return provider(prompt);
  }

  // Fallback: return original text (no real translation without a provider).
  return text;
}

module.exports = { translate };
