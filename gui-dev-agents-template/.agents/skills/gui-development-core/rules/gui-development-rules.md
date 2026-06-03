# GUI Development Rules

## Purpose

Universal rules for building production-quality GUI applications across all frameworks. These rules enforce architectural patterns, responsive design, accessibility, and cross-platform compatibility.

## Core Principles

### 1. Architecture Separation
- **MVC/MVVM Pattern**: Strict separation between UI and business logic
- **Event-Driven**: Use framework-appropriate event handling (signals/slots, callbacks, events)
- **Testability**: Logic layer must be testable without UI dependencies

### 2. Threading & Performance
- **Never Block UI Thread**: All I/O, network, and computation must run in background
- **Progress Feedback**: Long operations show progress indicators
- **Cancellation**: Background operations should be cancellable
- **Memory Management**: Clean up listeners, timers, and subscriptions

### 3. Responsive Design
- **No Hardcoded Pixels**: Use relative units and layout managers
- **DPI Awareness**: Support different screen densities (1x, 2x, 3x)
- **Breakpoints**: Define standard sizes for mobile/tablet/desktop
- **Orientation**: Support both portrait and landscape modes
- **Text Scaling**: Respect system font size preferences

### 4. Theming & Styling
- **Centralized Themes**: Single source of truth for colors, fonts, spacing
- **Dark/Light Mode**: Support both with smooth transitions
- **Consistent Spacing**: Use standard spacing scale (4px, 8px, 16px, 24px, 32px)
- **Color Contrast**: Meet WCAG AA standards (4.5:1 for text)

### 5. Accessibility
- **Keyboard Navigation**: All features accessible via keyboard
- **Screen Reader**: Semantic labels and descriptions
- **Focus Management**: Visible focus indicators, logical tab order
- **Touch Targets**: Minimum 44x44px for interactive elements
- **Error Messages**: Clear, actionable feedback

### 6. Cross-Platform
- **Platform Detection**: Adapt to OS-specific conventions
- **Native Dialogs**: Use system file/folder pickers
- **Keyboard Shortcuts**: Use platform conventions (Ctrl vs Cmd)
- **Font Rendering**: Test text on all target platforms

## Framework-Specific Guidelines

### Qt-Based (PySide6/PyQt6)
- Use Signal/Slot for all UI-to-logic communication
- Apply QSS at QApplication level
- Use QThread or QRunnable for background work
- Set parent for all QObject subclasses
- Use layout managers: QVBoxLayout, QHBoxLayout, QGridLayout

### Web-Based (React/Electron)
- Use hooks for state management
- Implement custom hooks for business logic
- Use CSS-in-JS or CSS modules for scoping
- Web Workers for heavy computation
- Semantic HTML for accessibility

### Flutter
- Use Provider, Riverpod, or BLoC for state management
- Apply Theme at MaterialApp level
- Use isolates for background computation
- Responsive with LayoutBuilder and MediaQuery

### Tkinter
- Use controller pattern for logic separation
- threading.Thread with queue.Queue for background work
- Configure styles at root window level
- Use pack(), grid() with relative sizing

## Anti-Patterns to Avoid

❌ **Direct UI-to-Model Calls**
- Creates untestable coupling
- ✅ Use controller/mediator layer

❌ **Blocking I/O on Main Thread**
- Freezes UI, poor UX
- ✅ Background threads with callbacks

❌ **Inline Styles Everywhere**
- Inconsistent theming
- ✅ Central theme system

❌ **Hardcoded Pixel Positions**
- Breaks on different DPIs
- ✅ Layout managers and relative units

❌ **Ignoring Accessibility**
- Legal liability, excludes users
- ✅ Full keyboard navigation + screen reader

❌ **Platform Assumptions**
- Breaks on other OS
- ✅ Test on all targets

## Code Review Checklist

### Architecture
- [ ] UI and logic layers are separated
- [ ] No business logic in view layer
- [ ] Controllers/ViewModels mediate between layers
- [ ] Dependencies are injected, not hardcoded

### Performance
- [ ] No blocking operations on UI thread
- [ ] Long operations show progress feedback
- [ ] Lists use virtualization for 100+ items
- [ ] Images are optimized and lazy-loaded
- [ ] Event handlers are debounced where appropriate

### Styling
- [ ] Styles come from central theme system
- [ ] No inline styles or hardcoded colors
- [ ] Dark mode is supported
- [ ] Spacing follows consistent scale
- [ ] Colors meet WCAG AA contrast standards

### Responsiveness
- [ ] No hardcoded pixel sizes
- [ ] Layout adapts to window resize
- [ ] Supports different screen densities
- [ ] Text scales with system preferences
- [ ] Touch targets are at least 44x44px

### Accessibility
- [ ] All interactive elements are keyboard accessible
- [ ] Tab order is logical
- [ ] Focus indicators are visible
- [ ] Screen reader labels are present
- [ ] Form validation provides clear errors

### Cross-Platform
- [ ] Tested on all target platforms
- [ ] Platform-specific code is isolated
- [ ] Native system dialogs are used
- [ ] Keyboard shortcuts follow platform conventions
- [ ] Font rendering verified on all platforms

## Testing Strategy

### Unit Tests
- Test business logic in isolation
- Mock external dependencies
- Cover edge cases and error paths

### Widget/Component Tests
- Test UI components with mocked dependencies
- Verify state changes
- Test user interactions

### Integration Tests
- Test UI-to-logic communication
- Verify data flow through layers
- Test with real dependencies

### E2E Tests
- Test complete user workflows
- Verify cross-component interactions
- Test on real platforms

### Accessibility Tests
- Run automated tools (axe, WAVE)
- Manual screen reader testing
- Keyboard-only navigation testing

### Visual Regression Tests
- Capture screenshots of components
- Compare against baseline
- Catch unintended visual changes

## Performance Optimization

### Rendering
- Only render what's visible (virtualization)
- Debounce rapid updates (scroll, resize)
- Memoize expensive computations
- Use keys for list items

### Memory
- Clean up event listeners on unmount
- Cancel pending async operations
- Dispose of timers and subscriptions
- Profile memory usage regularly

### Assets
- Compress images
- Use vector graphics (SVG) where possible
- Lazy load non-critical assets
- Bundle split for large apps

## Security Considerations

- Validate all user input
- Sanitize data before rendering
- Use parameterized queries for database
- Never expose sensitive data in client code
- Keep dependencies updated
- Use HTTPS for all network calls

## Integration Points

See [SKILL.md](../SKILL.md) for complete documentation and framework-specific patterns.
