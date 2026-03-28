'use strict';

const { summarize } = require('../skills/summarize');
const { translate } = require('../skills/translate');

/**
 * ResearchAgent – an agent that takes a list of text snippets, summarises
 * each one, and optionally combines them into a single research brief.
 *
 * Usage:
 *   const agent = new ResearchAgent({ provider });
 *   const brief = await agent.compile(snippets, { targetLanguage });
 */
class ResearchAgent {
  /**
   * @param {object} [options]
   * @param {Function} [options.provider] - LLM provider function.
   */
  constructor(options = {}) {
    this.provider = options.provider || null;
  }

  /**
   * Summarise each snippet and join them into a research brief.
   *
   * @param {string[]} snippets - Array of text snippets to process.
   * @param {object} [options]
   * @param {string} [options.targetLanguage] - Optional language for the final brief.
   * @returns {Promise<{summaries: string[], brief: string}>}
   */
  async compile(snippets, options = {}) {
    if (!Array.isArray(snippets) || snippets.length === 0) {
      throw new Error('ResearchAgent.compile: snippets must be a non-empty array');
    }

    const summaries = await Promise.all(
      snippets.map((snippet) => summarize(snippet, this.provider))
    );

    let brief = summaries.join(' ');

    if (options.targetLanguage) {
      brief = await translate(brief, options.targetLanguage, this.provider);
    }

    return { summaries, brief };
  }
}

module.exports = { ResearchAgent };
