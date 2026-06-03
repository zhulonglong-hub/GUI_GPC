# GUI Development Agents Template

A drop-in `.agents` template for GUI projects. Copy the `.agents` folder into any project and Claude will automatically apply the right rules for your framework.

## Quick Start

```
your-project/
├── .agents/          ← copy this entire folder from the template
├── src/
└── ...
```

That's it. Claude picks up the skills automatically when you open the project.

---

## What's Included

### Core Skill — always active

| Skill | Trigger globs | What it enforces |
|-------|--------------|-----------------|
| `gui-development-core` | `**/ui/**`, `**/views/**`, `**/components/**`, `**/*_widget.*`, `**/*_window.*` | MVC/MVVM separation, threading, theming, responsive layout, accessibility, cross-platform |

### Framework Skills — activate by framework

| Skill | Use when | Key rules |
|-------|----------|-----------|
| `pyside6-rules` | PySide6 / PyQt6 projects | Signal/Slot, QThread, QSS, QObject lifetime |
| `react-gui-rules` | React / Electron / Next.js | Custom hooks, semantic HTML, CSS variables, Web Workers |
| `flutter-rules` | Flutter / Dart projects | BLoC/Riverpod, ThemeData, isolates, LayoutBuilder |

---

## How to Use

### Option 1 — Invoke a skill directly

Type a slash command in the chat:

```
/gui-development-core     # universal rules
/pyside6-rules            # PySide6/PyQt6 specific
/react-gui-rules          # React/Electron specific
/flutter-rules            # Flutter/Dart specific
```

### Option 2 — Claude auto-applies rules

When you open or edit a matching file, Claude reads the relevant SKILL.md and applies its rules automatically. No command needed.

### Option 3 — Reference in a prompt

```
Review this widget against the gui-development-core rules.
Refactor this component following react-gui-rules.
```

---

## Customising for Your Project

### Add a project-specific skill

```
.agents/skills/my-project-rules/
├── SKILL.md          ← main rules document
├── commands/
│   └── my-project-rules.md
├── rules/
│   └── my-project-rules.md
└── schemas/
    └── input.schema.json
```

Minimal `SKILL.md` frontmatter:

```yaml
---
name: my-project-rules
description: One-line summary of what this skill enforces
version: 1.0.0
category: Languages
tags: [your, tags]
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, Glob, Grep]
globs: ['**/your-pattern/**/*']
---
```

### Extend an existing skill

Edit the relevant `SKILL.md` directly. Add project-specific iron laws, anti-patterns, or code examples under a `## Project Overrides` section.

### Disable a skill

Remove its folder from `.agents/skills/`, or set `user_invocable: false` and remove the `globs` entry so it never auto-triggers.

---

## Universal Iron Laws (summary)

These apply regardless of framework:

1. **Architecture** — strict MVC/MVVM; UI layer never calls model directly
2. **Threading** — never block the main/UI thread with I/O or computation
3. **Theming** — single central style system; no inline styles
4. **Layout** — no hardcoded pixel sizes; use layout managers / flex / grid
5. **Accessibility** — keyboard navigation, screen reader labels, WCAG AA contrast
6. **Cross-platform** — test on all target platforms before shipping

---

## Framework Decision Guide

| Need | Recommended framework |
|------|----------------------|
| Python desktop, scientific/ML tools | PySide6 |
| Python desktop, simple tooling | Tkinter |
| Web app or Electron desktop | React + TypeScript |
| Mobile + desktop from one codebase | Flutter |
| Desktop with minimal runtime overhead | Tauri (Rust + any JS framework) |
| Lightweight Python GUI | PySimpleGUI / DearPyGui |

---

## Memory Protocol

Each skill reads and writes to `.claude/context/memory/learnings.md`.

Create this file at project root to persist knowledge across sessions:

```
.claude/
└── context/
    └── memory/
        └── learnings.md   ← Claude records patterns and gotchas here
```

Starter content for `learnings.md`:

```markdown
# Project GUI Learnings

## Framework
[e.g. PySide6 6.7 on Windows 11]

## Architecture Notes
[Describe your MVC/MVVM structure]

## Known Platform Issues
[Any platform-specific rendering quirks]

## Patterns We Use
[Project-specific Signal/Slot patterns, component conventions, etc.]

## Patterns We Avoid
[Anti-patterns found in this codebase]
```

---

## Template File Structure

```
gui-dev-agents-template/
└── .agents/
    └── skills/
        ├── gui-development-core/        ← universal rules
        │   ├── SKILL.md
        │   ├── commands/
        │   │   └── gui-development-core.md
        │   ├── hooks/
        │   │   ├── pre-execute.cjs
        │   │   └── post-execute.cjs
        │   ├── references/
        │   │   └── research-requirements.md
        │   ├── rules/
        │   │   └── gui-development-rules.md
        │   ├── schemas/
        │   │   ├── input.schema.json
        │   │   └── output.schema.json
        │   ├── scripts/
        │   │   └── main.cjs
        │   └── templates/
        │       └── implementation-template.md
        ├── pyside6-rules/               ← PySide6/PyQt6
        │   ├── SKILL.md
        │   ├── commands/
        │   ├── rules/
        │   └── schemas/
        ├── react-gui-rules/             ← React/Electron
        │   ├── SKILL.md
        │   ├── commands/
        │   ├── rules/
        │   └── schemas/
        └── flutter-rules/               ← Flutter/Dart
            ├── SKILL.md
            ├── commands/
            ├── rules/
            └── schemas/
```

---

## Adding More Frameworks

To add Tkinter, Vue, Svelte, Tauri, or any other framework:

1. Copy `pyside6-rules/` as a starting point
2. Rename the folder and update `name:` in `SKILL.md`
3. Replace the iron laws and code examples with framework-specific content
4. Update `globs:` to match your framework's file patterns
5. Update `tags:` accordingly

---

*Template version 1.0.0 — copy `.agents/` into any GUI project to use.*
