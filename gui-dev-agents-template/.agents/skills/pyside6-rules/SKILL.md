---
name: pyside6-rules
description: PySide6/PyQt6 desktop GUI rules — Signal/Slot architecture, QSS theming, QThread concurrency, layout management, object lifetime, and cross-platform Qt rendering.
version: 1.0.0
category: Languages
agents: [python-pro, developer]
tags: [pyside6, pyqt6, python, gui, desktop, qt, signals-slots, qss, qthread]
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, PowerShell, Glob, Grep]
globs: ['**/ui/**/*.py', '**/*_ui.py', '**/*_dialog.py', '**/*_window.py', '**/*_widget.py', '**/*.qss']
best_practices:
  - Use Signal/Slot for all UI-to-logic communication
  - Never block the main thread
  - Apply QSS at QApplication level
  - Use layout managers, never absolute coordinates
  - Always set parent for QObject subclasses
error_handling: graceful
streaming: supported
verified: true
lastVerifiedAt: '2026-06-02'
source: custom
---

# PySide6 / PyQt6 Rules Skill

<identity>
PySide6 and PyQt6 desktop GUI specialist enforcing Signal/Slot architecture, QSS theming, QThread concurrency, layout management, and Qt object lifetime rules for production-quality desktop applications.
</identity>

## Iron Laws

1. **ALWAYS** use Signal/Slot for UI-to-logic communication — never call model methods directly from view
2. **NEVER** block the main thread — use QThread, QRunnable, or qasync for all I/O and computation
3. **ALWAYS** apply QSS at QApplication level — never inline per-widget styles
4. **NEVER** use absolute pixel coordinates — use QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout
5. **ALWAYS** set parent on QObject subclasses — prevents premature GC destroying C++ objects
6. **ALWAYS** use `@Slot()` decorator on slot methods — ensures type-safe cross-thread delivery

## Core Patterns

### MVC Architecture

```python
# model.py — pure business logic, zero Qt imports
class AppModel:
    def __init__(self):
        self._data = []

    def add(self, item: str) -> bool:
        if item and item not in self._data:
            self._data.append(item)
            return True
        return False

    def all(self) -> list:
        return self._data.copy()


# controller.py — mediates between model and view
from PySide6.QtCore import QObject, Signal, Slot

class AppController(QObject):
    data_changed = Signal(list)
    error_raised  = Signal(str)

    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)
        self._model = model

    @Slot(str)
    def add_item(self, text: str) -> None:
        if self._model.add(text):
            self.data_changed.emit(self._model.all())
        else:
            self.error_raised.emit(f"Cannot add: {text!r}")


# view.py — UI only, wired via signals/slots
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel
from PySide6.QtCore import Slot

class MainWindow(QMainWindow):
    def __init__(self, controller: AppController, parent=None):
        super().__init__(parent)
        self._ctrl = controller

        # Build UI
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._input = QLineEdit(central)
        self._btn   = QPushButton("Add", central)
        self._list  = QListWidget(central)
        self._error = QLabel(central)

        layout.addWidget(self._input)
        layout.addWidget(self._btn)
        layout.addWidget(self._list, stretch=1)
        layout.addWidget(self._error)

        # Wire signals
        self._btn.clicked.connect(self._on_add)
        self._ctrl.data_changed.connect(self._on_data_changed)
        self._ctrl.error_raised.connect(self._error.setText)

    @Slot()
    def _on_add(self) -> None:
        self._ctrl.add_item(self._input.text())
        self._input.clear()

    @Slot(list)
    def _on_data_changed(self, items: list) -> None:
        self._list.clear()
        self._list.addItems(items)
```

### Background Threading

```python
from PySide6.QtCore import QThread, Signal, Slot
from typing import Callable

class WorkerThread(QThread):
    progress       = Signal(int)          # 0-100
    result_ready   = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, task_fn: Callable, parent=None):
        super().__init__(parent)
        self._task_fn = task_fn
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._task_fn(
                progress_cb=self.progress.emit,
                cancelled_cb=lambda: self._cancelled,
            )
            if not self._cancelled:
                self.result_ready.emit(result)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
```

### QSS Theming

```python
# main.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
qss_path = Path(__file__).parent / "styles" / "dark.qss"
app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
```

```css
/* styles/dark.qss */
QMainWindow, QDialog {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 16px;
    color: #e0e0e0;
    min-width: 80px;
}

QPushButton:hover    { background-color: #4c5052; }
QPushButton:pressed  { background-color: #2d5a8e; }
QPushButton:disabled { color: #666666; }

QLineEdit {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px 8px;
    color: #e0e0e0;
    selection-background-color: #2d5a8e;
}

QListWidget {
    background-color: #313335;
    border: 1px solid #555555;
    outline: none;
}

QListWidget::item:selected { background-color: #2d5a8e; }
QListWidget::item:hover    { background-color: #3d4042; }
```

### Object Lifetime (Critical)

```python
# ❌ Wrong: timer is GC'd when function returns, C++ object destroyed
def bad_timer():
    t = QTimer()
    t.timeout.connect(do_work)
    t.start(1000)

# ✅ Correct: store as instance attribute OR set parent
class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)          # parent keeps it alive
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1000)

    @Slot()
    def _on_tick(self) -> None:
        pass
```

### Responsive Layout

```python
# ✅ Correct: layout managers
layout = QVBoxLayout()
layout.setContentsMargins(16, 16, 16, 16)
layout.setSpacing(8)

toolbar = QToolBar()
content = QSplitter(Qt.Orientation.Horizontal)
status  = QStatusBar()

layout.addWidget(toolbar)
layout.addWidget(content, stretch=1)   # fills remaining space
layout.addWidget(status)

# Grid with stretchy columns
grid = QGridLayout()
grid.addWidget(QLabel("Name:"), 0, 0)
grid.addWidget(QLineEdit(),     0, 1)
grid.setColumnStretch(1, 1)            # column 1 grows
```

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| `view.model.do_thing()` direct call | Emit a signal; connect to controller slot |
| `time.sleep()` in main thread | Use QThread / QTimer |
| `widget.setStyleSheet("color:red")` | Define rule in global QSS |
| `widget.setGeometry(10, 10, 200, 40)` | Use layout managers |
| Forgetting `@Slot()` on cross-thread handler | Add `@Slot(ArgType)` decorator |
| Creating `QTimer()` in a function without parent | Set `parent=self` or store as `self._timer` |

## PySide6 vs PyQt6 API Map

| PySide6 | PyQt6 |
|---------|-------|
| `Signal(int)` | `pyqtSignal(int)` |
| `@Slot(str)` | `@pyqtSlot(str)` |
| `Qt.AlignmentFlag.AlignCenter` | same |
| `Property(type, fget, fset)` | `pyqtProperty(type, fget, fset)` |

## Memory Protocol

**Before**: Read `.claude/context/memory/learnings.md` for prior Qt patterns.
**After**: Record platform-specific rendering issues, Signal/Slot patterns, or QThread gotchas.
