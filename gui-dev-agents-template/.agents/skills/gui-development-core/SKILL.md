---
name: gui-development-core
description: Universal GUI development rules enforcing MVC/MVVM patterns, responsive design, accessibility, threading best practices, and cross-platform compatibility for desktop/web GUI frameworks
version: 1.0.0
category: Languages
agents: [developer, frontend-pro, python-pro]
tags: [gui, desktop, web, ui, ux, mvc, mvvm, accessibility, responsive, threading]
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, PowerShell, Glob, Grep]
globs: ['**/ui/**/*.*', '**/views/**/*.*', '**/components/**/*.*', '**/*_ui.*', '**/*_view.*', '**/*_widget.*', '**/*_window.*', '**/*_dialog.*', '**/gui/**/*.*']
best_practices:
  - Enforce strict MVC/MVVM separation between UI and business logic
  - Never block the main UI thread with long-running operations
  - Use framework-appropriate state management patterns
  - Implement responsive layouts that adapt to different screen sizes and DPI settings
  - Follow WCAG 2.1 AA accessibility guidelines
  - Apply consistent theming and styling at the application level
  - Test on all target platforms before release
error_handling: graceful
streaming: supported
verified: true
lastVerifiedAt: '2026-06-02'
source: custom
trust_score: 100
provenance_sha: gui001template
---

# GUI Development Core Skill

<identity>
Universal GUI development specialist enforcing architectural patterns (MVC/MVVM), responsive design, accessibility standards, threading best practices, and cross-platform compatibility across multiple GUI frameworks (PySide6/PyQt6, Tkinter, Electron, React, Flutter, etc.).
</identity>

<capabilities>
- Design MVC/MVVM-separated application architectures
- Implement framework-appropriate event handling and state management
- Configure application-level theming and styling systems
- Manage background operations with framework-specific threading patterns
- Build responsive layouts that work across different screen sizes and DPIs
- Implement accessibility features (screen readers, keyboard navigation, ARIA)
- Set up cross-platform builds and platform-specific adaptations
- Optimize rendering performance and memory usage
</capabilities>

## Overview

This skill provides framework-agnostic rules for building production-quality GUI applications. The core principles apply universally: strict separation between UI and logic, non-blocking UI operations, consistent theming, responsive design, and accessibility compliance. Specific implementation patterns adapt to your chosen framework.

## When to Use

- When starting a new GUI application project
- When refactoring existing GUI code to improve architecture
- When debugging unresponsive UIs or performance issues
- When implementing accessibility or responsive design features
- When preparing for cross-platform deployment
- When code review reveals architectural or UX issues

## Universal Iron Laws

### 1. Architecture: Separation of Concerns

**ALWAYS** separate presentation from business logic using MVC, MVVM, or similar patterns.

- **Why**: Direct coupling makes code untestable, unmaintainable, and platform-locked
- **How**: UI layer only handles rendering and user events; logic layer has no UI dependencies
- **Frameworks**:
  - **PySide6/PyQt6**: Use Signal/Slot for UI-to-logic communication
  - **React**: Use hooks + custom hooks for business logic
  - **Flutter**: Use Provider, Riverpod, or BLoC pattern
  - **Electron**: IPC between renderer and main process
  - **Tkinter**: Command pattern with callbacks to controller layer

### 2. Threading: Never Block the UI Thread

**NEVER** perform long-running operations (I/O, network, computation) on the main UI thread.

- **Why**: Blocking the event loop freezes the interface and triggers "not responding" dialogs
- **How**: Offload work to background threads/workers with progress callbacks
- **Frameworks**:
  - **PySide6/PyQt6**: QThread, QRunnable, or qasync
  - **React/Electron**: Web Workers, async/await, or child processes
  - **Flutter**: isolates or compute()
  - **Tkinter**: threading.Thread with queue.Queue for communication

### 3. Theming: Centralized Styling

**ALWAYS** apply styles at the application or component-system level, not per-widget inline.

- **Why**: Inline styles create inconsistency and make theming impossible
- **How**: Define a single source of truth for colors, fonts, spacing
- **Frameworks**:
  - **PySide6/PyQt6**: QSS stylesheet at QApplication level
  - **React**: CSS modules, styled-components, or Tailwind
  - **Flutter**: ThemeData at MaterialApp level
  - **Electron**: Global CSS + CSS variables

### 4. Layout: Responsive & DPI-Aware

**NEVER** use hardcoded pixel positions or sizes. Use layout managers/flex systems.

- **Why**: Different screen sizes, DPI scaling, and platforms break fixed layouts
- **How**: Use framework layout systems that adapt to container size
- **Frameworks**:
  - **PySide6/PyQt6**: QVBoxLayout, QHBoxLayout, QGridLayout
  - **React**: Flexbox, CSS Grid
  - **Flutter**: Column, Row, Stack, Flexible
  - **Tkinter**: pack(), grid(), place() with relative sizing

### 5. Accessibility: Inclusive by Default

**ALWAYS** implement keyboard navigation, screen reader support, and WCAG compliance.

- **Why**: Legal requirements (ADA, AODA) and ethical responsibility
- **How**: Semantic markup, ARIA labels, focus management, sufficient contrast
- **Frameworks**:
  - **Web (React/Electron)**: Semantic HTML, ARIA attributes
  - **PySide6/PyQt6**: setAccessibleName(), setAccessibleDescription()
  - **Flutter**: Semantics widget
  - **Tkinter**: focus_set(), binding keyboard shortcuts

### 6. Cross-Platform: Test on All Targets

**ALWAYS** test on all target platforms (Windows, macOS, Linux, mobile) before release.

- **Why**: Rendering, fonts, DPI, and widget behavior differ significantly
- **How**: Set up CI/CD for multi-platform builds and manual testing
- **Platform-specific issues**:
  - Font scaling (Windows vs macOS)
  - Native file dialogs
  - Window decorations and system tray
  - Keyboard shortcuts (Ctrl vs Cmd)

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|--------------|------------------|
| Direct UI-to-model calls | Untestable, unmaintainable coupling | Use controller/mediator with event bus |
| Blocking I/O on main thread | UI freezes, poor UX | Background threads with progress updates |
| Inline styles everywhere | Inconsistent theming, maintenance hell | Central theme system |
| Hardcoded pixel sizes | Breaks on different DPIs/screens | Relative units and layout managers |
| Ignoring keyboard users | Accessibility violations, poor UX | Full keyboard navigation + focus management |
| Platform assumptions | Breaks on other OS | Platform detection and conditional rendering |

## Framework-Specific Patterns

### PySide6 / PyQt6 (Qt)

```python
# MVC with Signal/Slot
from PySide6.QtCore import QObject, Signal, Slot

class Controller(QObject):
    data_loaded = Signal(list)
    
    @Slot()
    def load_data(self):
        # Background thread
        worker = WorkerThread(self.fetch_data)
        worker.finished.connect(lambda data: self.data_loaded.emit(data))
        worker.start()

# QSS Theming
app.setStyleSheet("""
    QMainWindow { background: #2b2b2b; }
    QPushButton { 
        background: #3c3f41;
        border-radius: 4px;
        padding: 8px 16px;
    }
""")
```

### React (Web/Electron)

```typescript
// Custom hook for logic separation
function useDataLoader() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const loadData = async () => {
    setLoading(true);
    const result = await fetch('/api/data');
    setData(await result.json());
    setLoading(false);
  };
  
  return { data, loading, loadData };
}

// Component uses hook
function DataView() {
  const { data, loading, loadData } = useDataLoader();
  // ... render logic
}
```

### Flutter

```dart
// BLoC pattern
class DataBloc extends Bloc<DataEvent, DataState> {
  DataBloc() : super(DataInitial()) {
    on<LoadData>((event, emit) async {
      emit(DataLoading());
      try {
        final data = await repository.fetchData();
        emit(DataLoaded(data));
      } catch (e) {
        emit(DataError(e.toString()));
      }
    });
  }
}

// Theme
MaterialApp(
  theme: ThemeData(
    primarySwatch: Colors.blue,
    brightness: Brightness.dark,
  ),
  // ...
)
```

### Tkinter

```python
# Controller pattern
class Controller:
    def __init__(self, view, model):
        self.view = view
        self.model = model
        
    def load_data(self):
        def worker():
            data = self.model.fetch_data()
            self.view.after(0, lambda: self.view.update_list(data))
        
        threading.Thread(target=worker, daemon=True).start()

# View
class MainView(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        # UI setup with grid/pack
```

## Accessibility Checklist

- [ ] All interactive elements are keyboard accessible
- [ ] Tab order is logical and predictable
- [ ] Focus indicators are visible
- [ ] Screen reader labels are present and descriptive
- [ ] Color contrast meets WCAG AA (4.5:1 for text, 3:1 for UI components)
- [ ] Text is resizable without breaking layout
- [ ] No flashing content (seizure risk)
- [ ] Form validation provides clear error messages
- [ ] All functionality available via keyboard
- [ ] Semantic HTML/native widgets used where possible

## Responsive Design Principles

1. **Mobile-first**: Design for smallest screen, enhance for larger
2. **Breakpoints**: Define standard sizes (mobile, tablet, desktop)
3. **Flexible grids**: Use percentages or fr units, not fixed pixels
4. **Scalable assets**: Use SVG or high-DPI images
5. **Touch targets**: Minimum 44x44px for mobile
6. **Text scaling**: Support system font size preferences
7. **Orientation**: Support both portrait and landscape

## Performance Optimization

- **Lazy loading**: Load UI components on-demand
- **Virtualization**: For long lists, only render visible items
- **Debouncing**: Limit rapid event handler calls (resize, scroll)
- **Memoization**: Cache expensive renders (React.memo, useMemo)
- **Asset optimization**: Compress images, bundle split
- **Memory management**: Clean up listeners, timers, subscriptions

## Testing Strategy

1. **Unit tests**: Test business logic in isolation
2. **Widget/Component tests**: Test UI components with mocked dependencies
3. **Integration tests**: Test UI-to-logic communication
4. **E2E tests**: Test full user flows
5. **Accessibility audit**: axe, WAVE, or manual screen reader testing
6. **Visual regression**: Catch unintended UI changes
7. **Cross-platform**: Test on all target environments

## Memory Protocol

**Before starting**: Read `.claude/context/memory/learnings.md` for project-specific GUI patterns.

**After completing**: Record framework-specific gotchas, platform workarounds, or accessibility solutions to `.claude/context/memory/learnings.md`.

## Complementary Skills

| Skill | Relationship |
|-------|-------------|
| `pyside6-ui-development-rules` | Specialized Qt/PySide6 patterns |
| `react-best-practices` | React-specific patterns |
| `accessibility` | Deeper WCAG compliance auditing |
| `tdd` | Test-driven development for GUI testing |
| `modern-python` | Python project setup (for Python GUIs) |

## Quick Start Guide

1. **Choose your framework** based on requirements:
   - Desktop cross-platform: PySide6, Flutter, Electron
   - Web: React, Vue, Svelte
   - Native mobile: Flutter, React Native
   - Lightweight: Tkinter (Python), Tauri (Rust+JS)

2. **Set up architecture**:
   - Create separate modules for UI, logic, and data
   - Define clear interfaces between layers
   - Choose state management pattern

3. **Configure tooling**:
   - Linter/formatter
   - Type checking
   - Testing framework
   - Build system

4. **Implement incrementally**:
   - Start with core workflow
   - Add features one at a time
   - Test continuously
   - Refactor before it hurts

5. **Polish**:
   - Apply consistent theming
   - Audit accessibility
   - Test cross-platform
   - Optimize performance

---

*This skill provides universal guidelines. Invoke framework-specific skills for detailed patterns.*
