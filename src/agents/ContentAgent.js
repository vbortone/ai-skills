'use strict';

const { summarize } = require('../skills/summarize');
const { classify } = require('../skills/classify');
const { translate } = require('../skills/translate');

/**
 * ContentAgent – an agent that analyses a piece of content by running
 * multiple skills in sequence and returning a structured result.
 *
 * Usage:
 *   const agent = new ContentAgent({ provider });
 *   const result = await agent.analyse(text, { labels, targetLanguage });
 */
class ContentAgent {
  /**
   * @param {object} [options]
   * @param {Function} [options.provider] - LLM provider function shared by all skills.
   */
  constructor(options = {}) {
    this.provider = options.provider || null;
  }

  /**
   * Analyse text by summarising, classifying, and optionally translating it.
   *
   * @param {string} text - The input text.
   * @param {object} [options]
   * @param {string[]} [options.labels] - Labels for classification.
   * @param {string} [options.targetLanguage] - Translate the summary into this language.
   * @returns {Promise<{summary: string, label: string, translation: string|null}>}
   */
  async analyse(text, options = {}) {
    const { labels = ['positive', 'negative', 'neutral'], targetLanguage } = options;

    const [summary, label] = await Promise.all([
      summarize(text, this.provider),
      classify(text, labels, this.provider),
    ]);

    let translation = null;
    if (targetLanguage) {
      translation = await translate(summary, targetLanguage, this.provider);
    }

    return { summary, label, translation };
  }
}

module.exports = { ContentAgent };
