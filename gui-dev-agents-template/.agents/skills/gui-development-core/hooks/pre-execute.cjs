#!/usr/bin/env node
'use strict';
/**
 * pre-execute hook — runs before the gui-development-core skill executes.
 * Validates input and checks for required context.
 */

const args = process.argv.slice(2);
const input = args[0] ? JSON.parse(args[0]) : {};

const warnings = [];

// Warn if no framework specified
if (!input.framework) {
  warnings.push('No framework specified. Universal rules will apply. Pass --framework for specific guidance.');
}

// Warn if no target specified
if (!input.target) {
  warnings.push('No target file or directory specified. Running in general mode.');
}

if (warnings.length > 0) {
  warnings.forEach(w => console.warn('[gui-dev pre-execute]', w));
}

process.exit(0);
