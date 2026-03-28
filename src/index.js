'use strict';

/**
 * ai-skills – Personal AI skills and agents library.
 *
 * Skills  – focused, composable capabilities.
 * Agents  – higher-level orchestrators that combine multiple skills.
 */

const { summarize } = require('./skills/summarize');
const { classify } = require('./skills/classify');
const { translate } = require('./skills/translate');
const { ContentAgent } = require('./agents/ContentAgent');
const { ResearchAgent } = require('./agents/ResearchAgent');

module.exports = {
  // Skills
  summarize,
  classify,
  translate,

  // Agents
  ContentAgent,
  ResearchAgent,
};
