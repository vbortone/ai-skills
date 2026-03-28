'use strict';

/**
 * Classify skill – assigns a label from a predefined set to a piece of text.
 *
 * The `provider` parameter is expected to be an async function with the
 * signature:  provider(prompt: string) => Promise<string>
 *
 * When no provider is given the skill returns the label whose keyword appears
 * most frequently in the text (case-insensitive) as a simple baseline.
 */

/**
 * @param {string} text - The text to classify.
 * @param {string[]} labels - The candidate labels.
 * @param {Function} [provider] - Optional LLM provider function.
 * @returns {Promise<string>} The chosen label.
 */
async function classify(text, labels, provider) {
  if (typeof text !== 'string' || text.trim() === '') {
    throw new Error('classify: text must be a non-empty string');
  }
  if (!Array.isArray(labels) || labels.length === 0) {
    throw new Error('classify: labels must be a non-empty array');
  }

  if (provider) {
    const prompt =
      `Classify the following text into exactly one of these labels: ` +
      `${labels.join(', ')}.\n\nText: ${text}\n\nRespond with just the label.`;
    const result = await provider(prompt);
    return result.trim();
  }

  // Fallback: pick the label whose name appears most in the text.
  const lower = text.toLowerCase();
  let best = labels[0];
  let bestCount = 0;
  for (const label of labels) {
    const regex = new RegExp(label.toLowerCase(), 'g');
    const count = (lower.match(regex) || []).length;
    if (count > bestCount) {
      bestCount = count;
      best = label;
    }
  }
  return best;
}

module.exports = { classify };
