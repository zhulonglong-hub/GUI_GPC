---
name: react-gui-rules
description: React desktop/web GUI rules — hooks architecture, component design, state management, accessibility, responsive CSS, and performance patterns for React and Electron apps.
version: 1.0.0
category: Languages
agents: [frontend-pro, developer]
tags: [react, typescript, electron, gui, web, hooks, state, accessibility, css]
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, PowerShell, Glob, Grep]
globs: ['**/*.tsx', '**/*.jsx', '**/components/**/*', '**/views/**/*', '**/hooks/**/*', '**/*.css', '**/*.module.css']
best_practices:
  - Separate business logic into custom hooks
  - Keep components pure and focused on rendering
  - Use semantic HTML for accessibility
  - Apply styles via CSS modules or styled-components
  - Offload heavy work to Web Workers
error_handling: graceful
streaming: supported
verified: true
lastVerifiedAt: '2026-06-02'
source: custom
---

# React GUI Rules Skill

<identity>
React and Electron desktop/web GUI specialist enforcing hooks-based architecture, component design patterns, accessibility, responsive CSS, and performance optimisation for production applications.
</identity>

## Iron Laws

1. **ALWAYS** separate business logic into custom hooks — components should only render
2. **NEVER** perform expensive computation or blocking I/O on the render thread — use Web Workers or async
3. **ALWAYS** use semantic HTML elements — `<button>`, `<nav>`, `<main>`, never `<div onClick>`
4. **NEVER** mutate state directly — use setState / dispatch
5. **ALWAYS** provide ARIA labels for non-obvious interactive elements
6. **NEVER** use inline styles for theming — use CSS variables or a design token system

## Core Patterns

### Custom Hook for Logic Separation

```typescript
// hooks/useDataLoader.ts — all logic here, zero JSX
import { useState, useCallback } from 'react';

interface DataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useDataLoader<T>(fetcher: () => Promise<T>) {
  const [state, setState] = useState<DataState<T>>({
    data: null, loading: false, error: null,
  });

  const load = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcher();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: String(err) }));
    }
  }, [fetcher]);

  return { ...state, load };
}

// components/DataView.tsx — only rendering
import { useDataLoader } from '../hooks/useDataLoader';
import { fetchItems } from '../services/api';

export function DataView() {
  const { data, loading, error, load } = useDataLoader(fetchItems);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBanner message={error} onRetry={load} />;

  return (
    <ul role="list">
      {data?.map(item => <li key={item.id}>{item.name}</li>)}
    </ul>
  );
}
```

### Accessible Interactive Elements

```tsx
// ❌ Wrong: div with onClick — not keyboard accessible
<div onClick={handleDelete} className="btn">Delete</div>

// ✅ Correct: semantic button with ARIA
<button
  type="button"
  onClick={handleDelete}
  aria-label={`Delete ${item.name}`}
  disabled={isDeleting}
>
  {isDeleting ? 'Deleting…' : 'Delete'}
</button>
```

### CSS Variables Theming

```css
/* styles/tokens.css — single source of truth */
:root {
  --color-bg:        #1e1e2e;
  --color-surface:   #2a2a3d;
  --color-primary:   #7c6af7;
  --color-text:      #cdd6f4;
  --color-text-muted:#6e738d;
  --color-error:     #f38ba8;

  --radius-sm: 4px;
  --radius-md: 8px;

  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  --font-size-sm:   12px;
  --font-size-base: 14px;
  --font-size-lg:   18px;
}

/* components/Button.module.css */
.button {
  background: var(--color-primary);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  color: #fff;
  cursor: pointer;
  border: none;
  font-size: var(--font-size-base);
}

.button:hover  { filter: brightness(1.1); }
.button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
```

### Web Worker for Heavy Computation

```typescript
// workers/processor.worker.ts
self.onmessage = (e: MessageEvent) => {
  const result = heavyComputation(e.data);
  self.postMessage(result);
};

// hooks/useProcessor.ts
import { useCallback, useRef } from 'react';

export function useProcessor() {
  const workerRef = useRef<Worker | null>(null);

  const process = useCallback((data: unknown): Promise<unknown> => {
    return new Promise((resolve, reject) => {
      workerRef.current = new Worker(
        new URL('../workers/processor.worker.ts', import.meta.url)
      );
      workerRef.current.onmessage = e => resolve(e.data);
      workerRef.current.onerror   = e => reject(e.message);
      workerRef.current.postMessage(data);
    });
  }, []);

  return { process };
}
```

### Responsive Layout

```css
/* Responsive grid — no hardcoded pixel widths */
.layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-md);
  padding: var(--spacing-md);
}

/* Sidebar + content */
.app {
  display: grid;
  grid-template-columns: 240px 1fr;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
}

@media (max-width: 768px) {
  .app { grid-template-columns: 1fr; }
}
```

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| Logic inside component body | Extract to custom hook |
| `<div onClick>` for interactive elements | Use `<button>` or `<a>` |
| Inline `style={{ color: 'red' }}` for theming | CSS variable in token file |
| Mutation: `state.items.push(x)` | `setState(s => ({ ...s, items: [...s.items, x] }))` |
| Missing `key` on list items | Add stable unique `key` prop |
| Synchronous heavy computation in render | Move to Web Worker or `useMemo` |
| Missing error boundaries | Wrap route-level components in `<ErrorBoundary>` |

## Electron-Specific Notes

```typescript
// ✅ IPC for main↔renderer separation
// main.ts
ipcMain.handle('read-file', async (_event, filePath: string) => {
  return fs.promises.readFile(filePath, 'utf8');
});

// renderer
const content = await window.electronAPI.readFile(path);

// preload.ts — expose only what's needed
contextBridge.exposeInMainWorld('electronAPI', {
  readFile: (path: string) => ipcRenderer.invoke('read-file', path),
});
```

## Memory Protocol

**Before**: Read `.claude/context/memory/learnings.md` for prior React/Electron patterns.
**After**: Record component patterns, CSS gotchas, or Electron IPC patterns discovered.
