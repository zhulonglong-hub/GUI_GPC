#!/usr/bin/env node
'use strict';
/**
 * gui-development-core - GUI Development Skill Script
 */

const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith('--')) {
    const key = args[i].slice(2);
    const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[++i] : true;
    options[key] = value;
  }
}

if (options.help) {
  console.log(`
gui-development-core - Universal GUI Development Skill

Usage:
  node main.cjs --check <file>       Check a file against GUI guidelines
  node main.cjs --list               List all guidelines
  node main.cjs --framework <name>   Show framework-specific guidelines
  node main.cjs --help               Show this help

Frameworks supported:
  pyside6, pyqt6, tkinter, react, electron, flutter, tauri, vue, svelte

Description:
  Universal GUI development rules enforcing MVC/MVVM, responsive design,
  accessibility, threading, and cross-platform best practices.
`);
  process.exit(0);
}

if (options.list) {
  console.log('Guidelines for gui-development-core:');
  console.log('  1. Architecture: Strict MVC/MVVM separation');
  console.log('  2. Threading: Never block the UI thread');
  console.log('  3. Theming: Centralized styling system');
  console.log('  4. Layout: Responsive, no hardcoded pixels');
  console.log('  5. Accessibility: WCAG 2.1 AA compliance');
  console.log('  6. Cross-platform: Test on all targets');
  console.log('');
  console.log('See SKILL.md for full documentation.');
  process.exit(0);
}

if (options.framework) {
  const frameworks = {
    pyside6: 'Use Signal/Slot, QThread, QSS at QApplication level, layout managers',
    pyqt6: 'Use pyqtSignal/pyqtSlot, QThread, QSS at QApplication level, layout managers',
    tkinter: 'Use controller pattern, threading.Thread + queue.Queue, configure styles at root',
    react: 'Use hooks, custom hooks for logic, CSS modules, Web Workers',
    electron: 'IPC for main/renderer separation, Web Workers, global CSS variables',
    flutter: 'Use BLoC/Provider/Riverpod, isolates for heavy work, ThemeData',
    tauri: 'Rust backend via commands, async frontend, Tauri events',
    vue: 'Pinia/Vuex for state, composables for logic, scoped styles',
    svelte: 'Stores for state, derived stores, scoped CSS'
  };
  const fw = frameworks[options.framework.toLowerCase()];
  if (fw) {
    console.log(`${options.framework} guidelines: ${fw}`);
  } else {
    console.log(`Unknown framework: ${options.framework}`);
    console.log('Supported: ' + Object.keys(frameworks).join(', '));
  }
  process.exit(0);
}

console.log('gui-development-core skill loaded. Use with Claude for GUI code review and development.');
