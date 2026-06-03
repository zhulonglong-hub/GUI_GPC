#!/usr/bin/env node
'use strict';
/**
 * post-execute hook — runs after the gui-development-core skill executes.
 * Records learnings and suggests memory updates.
 */

const args = process.argv.slice(2);
const output = args[0] ? JSON.parse(args[0]) : {};

if (output.ok === false) {
  console.warn('[gui-dev post-execute] Skill reported failure. Review violations and fix before proceeding.');
}

if (output.violations && output.violations.length > 0) {
  const errors = output.violations.filter(v => v.severity === 'error');
  const warnings = output.violations.filter(v => v.severity === 'warning');
  console.log(`[gui-dev post-execute] Found ${errors.length} error(s), ${warnings.length} warning(s).`);
}

console.log('[gui-dev post-execute] Remember to update .claude/context/memory/learnings.md with any new patterns or platform-specific findings.');

process.exit(0);
