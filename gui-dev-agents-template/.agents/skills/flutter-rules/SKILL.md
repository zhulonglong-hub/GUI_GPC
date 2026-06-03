---
name: flutter-rules
description: Flutter GUI rules — BLoC/Provider state management, widget composition, responsive layouts, theming, isolates for background work, and cross-platform Flutter best practices.
version: 1.0.0
category: Languages
agents: [developer, mobile-pro]
tags: [flutter, dart, mobile, desktop, gui, bloc, provider, riverpod, material, cupertino]
model: sonnet
invoked_by: both
user_invocable: true
tools: [Read, Write, Edit, Bash, PowerShell, Glob, Grep]
globs: ['**/*.dart', '**/lib/**/*', '**/widgets/**/*', '**/screens/**/*', '**/pages/**/*', '**/blocs/**/*']
best_practices:
  - Use BLoC or Riverpod for state management
  - Keep widgets small and focused
  - Use isolates for heavy computation
  - Apply ThemeData at MaterialApp level
  - Use LayoutBuilder and MediaQuery for responsiveness
error_handling: graceful
streaming: supported
verified: true
lastVerifiedAt: '2026-06-02'
source: custom
---

# Flutter Rules Skill

<identity>
Flutter and Dart GUI specialist enforcing BLoC/Riverpod state management, widget composition, responsive layouts, ThemeData theming, and isolate-based background processing for cross-platform Flutter applications.
</identity>

## Iron Laws

1. **ALWAYS** use BLoC, Riverpod, or Provider for state — never raw setState in complex features
2. **NEVER** perform heavy computation on the main isolate — use `compute()` or `Isolate.spawn()`
3. **ALWAYS** apply theme via `ThemeData` at `MaterialApp` level — never inline widget colors
4. **NEVER** use hardcoded pixel sizes — use `MediaQuery`, `LayoutBuilder`, `Flexible`, `Expanded`
5. **ALWAYS** add `Semantics` widgets for accessibility on custom interactive widgets
6. **ALWAYS** dispose controllers, streams, and subscriptions in `dispose()`

## Core Patterns

### BLoC Pattern

```dart
// bloc/data_event.dart
abstract class DataEvent {}
class LoadData extends DataEvent {}
class AddItem extends DataEvent {
  final String item;
  AddItem(this.item);
}

// bloc/data_state.dart
abstract class DataState {}
class DataInitial  extends DataState {}
class DataLoading  extends DataState {}
class DataLoaded   extends DataState { final List<String> items; DataLoaded(this.items); }
class DataError    extends DataState { final String message; DataError(this.message); }

// bloc/data_bloc.dart
import 'package:flutter_bloc/flutter_bloc.dart';

class DataBloc extends Bloc<DataEvent, DataState> {
  final DataRepository _repo;

  DataBloc(this._repo) : super(DataInitial()) {
    on<LoadData>(_onLoad);
    on<AddItem>(_onAdd);
  }

  Future<void> _onLoad(LoadData event, Emitter<DataState> emit) async {
    emit(DataLoading());
    try {
      final items = await _repo.fetchAll();
      emit(DataLoaded(items));
    } catch (e) {
      emit(DataError(e.toString()));
    }
  }

  Future<void> _onAdd(AddItem event, Emitter<DataState> emit) async {
    final current = state;
    if (current is DataLoaded) {
      await _repo.add(event.item);
      emit(DataLoaded([...current.items, event.item]));
    }
  }
}

// ui: consume in widget
BlocBuilder<DataBloc, DataState>(
  builder: (context, state) {
    if (state is DataLoading) return const CircularProgressIndicator();
    if (state is DataError)   return Text('Error: ${state.message}');
    if (state is DataLoaded)  return ItemList(items: state.items);
    return const SizedBox.shrink();
  },
)
```

### Background Isolation

```dart
// For pure functions — use compute()
Future<List<Result>> processData(List<Input> inputs) async {
  return compute(_heavyProcessing, inputs);
}

List<Result> _heavyProcessing(List<Input> inputs) {
  // runs in a separate isolate
  return inputs.map((i) => Result.from(i)).toList();
}
```

### ThemeData Theming

```dart
MaterialApp(
  theme: ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xFF7C6AF7),
      brightness: Brightness.dark,
    ),
    useMaterial3: true,
    textTheme: const TextTheme(
      bodyMedium: TextStyle(fontSize: 14, height: 1.5),
      titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
    ),
    cardTheme: const CardTheme(
      elevation: 2,
      margin: EdgeInsets.all(8),
    ),
  ),
)
```

### Responsive Layout

```dart
// LayoutBuilder for container-based responsiveness
LayoutBuilder(
  builder: (context, constraints) {
    final isWide = constraints.maxWidth > 600;
    return isWide
        ? Row(children: [SideBar(), Expanded(child: Content())])
        : Column(children: [Content(), BottomNav()]);
  },
)

// MediaQuery for device-based
final screenWidth = MediaQuery.of(context).size.width;
final padding = screenWidth < 400
    ? const EdgeInsets.all(8)
    : const EdgeInsets.all(16);
```

### Proper Disposal

```dart
class _MyWidgetState extends State<MyWidget> {
  late final TextEditingController _ctrl;
  late final StreamSubscription<Event> _sub;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController();
    _sub  = eventStream.listen(_onEvent);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _sub.cancel();
    super.dispose();
  }
}
```

### Accessibility

```dart
// Add Semantics for custom widgets
Semantics(
  label: 'Delete item ${item.name}',
  button: true,
  child: GestureDetector(
    onTap: () => bloc.add(DeleteItem(item.id)),
    child: const Icon(Icons.delete),
  ),
)
```

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| `setState` for complex shared state | Use BLoC / Riverpod |
| Heavy computation in `build()` | Move to `compute()` or isolate |
| `Container(color: Color(0xFF...))` | Use `Theme.of(context).colorScheme` |
| `SizedBox(width: 320)` hardcoded | Use `LayoutBuilder` + `Flexible` |
| Missing `dispose()` for controllers | Always override `dispose()` |
| Deep widget nesting | Extract to named widget classes |

## Memory Protocol

**Before**: Read `.claude/context/memory/learnings.md` for prior Flutter patterns.
**After**: Record platform-specific rendering issues, BLoC patterns, or isolate gotchas.
