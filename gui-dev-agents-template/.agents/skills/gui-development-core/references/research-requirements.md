# Research Requirements for GUI Development

## Before Starting Any GUI Task

1. **Read existing code** — understand the current architecture before making changes
2. **Identify the framework** — check imports, package.json, requirements.txt, or pubspec.yaml
3. **Check the theme system** — find where global styles are defined
4. **Understand state management** — find the existing pattern (Signal/Slot, hooks, BLoC, etc.)
5. **Review threading approach** — how does the project handle background work?

## Framework Detection

### Python GUI
```
# Check requirements.txt or environment
grep -i "pyside6\|pyqt6\|tkinter\|wxpython\|kivy" requirements.txt
```

### Web/Electron
```
# Check package.json
cat package.json | grep -E "react|vue|svelte|electron|tauri"
```

### Flutter
```
# Check pubspec.yaml
cat pubspec.yaml | grep -E "flutter|dart"
```

## Architecture Research Questions

Before implementing any feature, answer:

1. **Where is the UI layer?** (views/, ui/, components/, widgets/)
2. **Where is the business logic?** (models/, services/, controllers/, blocs/)
3. **How does UI communicate with logic?** (signals, callbacks, events, state)
4. **Where is the theme defined?** (styles/, theme.qss, theme.css, ThemeData)
5. **How is threading handled?** (QThread, asyncio, Web Workers, isolates)

## Common Research Resources

### PySide6/PyQt6
- Qt documentation: https://doc.qt.io/qt-6/
- PySide6 docs: https://doc.qt.io/qtforpython-6/
- Qt Style Sheets reference: https://doc.qt.io/qt-6/stylesheet-reference.html

### React
- React docs: https://react.dev/
- React accessibility: https://react.dev/reference/react-dom/components/common#aria

### Flutter
- Flutter docs: https://docs.flutter.dev/
- Material Design: https://m3.material.io/

### Accessibility
- WCAG 2.1 guidelines: https://www.w3.org/TR/WCAG21/
- ARIA patterns: https://www.w3.org/WAI/ARIA/apg/patterns/

## Code Review Research

When reviewing GUI code, look for:

### Architecture violations
- [ ] UI methods calling model directly?
- [ ] Business logic in event handlers?
- [ ] Missing abstraction between layers?

### Performance issues
- [ ] Network/file I/O in main thread?
- [ ] Unthrottled event handlers?
- [ ] Unbounded list rendering?
- [ ] Memory leaks (uncleaned listeners)?

### Accessibility gaps
- [ ] Missing ARIA/accessible labels?
- [ ] Broken keyboard navigation?
- [ ] Low color contrast?
- [ ] Missing focus management?

### Cross-platform issues
- [ ] Hardcoded platform paths (backslash vs forward slash)?
- [ ] Missing DPI scaling?
- [ ] Platform-specific font sizes?
