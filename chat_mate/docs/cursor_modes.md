# 🗡️ Cursor Execution Modes

This document outlines the two core execution modes for Cursor operations in the ChatMate project.

## 🔺 Execution Modes Overview

### 1️⃣ FULL SYNC MODE (FSM)
- **Priority**: Speed, convergence, ship fast
- **Role**: Execute tightly defined tasks
- **Use Case**: Quick fixes, feature additions, bug fixes
- **Rules**: 
  - Tactical strikes only
  - No architectural changes
  - Follow Cursor Rules v1.0
  - Git commits after every stable pass

### 2️⃣ RED-GREEN-REFACTOR MODE (RGRM)
- **Priority**: Precision, stability, test-driven refactor cycles
- **Role**: Write tests, validate, refactor cleanly
- **Use Case**: Code refactoring, test coverage improvements
- **Rules**:
  - Red → Green → Refactor, enforced in order
  - No skipping phases
  - All commits follow the RGR cycle

## ✅ Mode Selection Guide

### When to Use FULL SYNC MODE
- Quick bug fixes
- Feature additions
- Documentation updates
- Configuration changes
- Performance optimizations (non-architectural)

### When to Use RED-GREEN-REFACTOR MODE
- Code refactoring
- Test coverage improvements
- Dependency injection
- Interface changes
- Architecture improvements

## 📂 Prompt Files

The execution mode prompts are stored in:
```
cursor_prompts/
├── full_sync_mode/
│   └── execution_prompt.md
└── red_green_refactor_mode/
    └── execution_prompt.md
```

## 🔄 Mode Switching

To switch between modes:
1. Review the appropriate prompt file
2. Follow the execution flow
3. Use the specified Git branch and commit rules
4. Complete all quality checks

## 📝 Git Workflow

### FULL SYNC MODE
```bash
git checkout -b feature/cursor-[task-name]
# ... execute task ...
git commit -m "Feature: [task description]. Next: [next step]."
```

### RED-GREEN-REFACTOR MODE
```bash
git checkout -b refactor/cursor-[task-name]
# Red Phase
git commit -m "Red: [test description]"
# Green Phase
git commit -m "Green: [implementation]"
# Refactor Phase
git commit -m "Refactor: [optimizations]"
```

## ✅ Quality Assurance

### FULL SYNC MODE Checks
- Code follows project style guide
- No architectural changes
- All tests pass
- Documentation updated if needed

### RED-GREEN-REFACTOR MODE Checks
- Tests are meaningful and cover edge cases
- Code follows project style guide
- No behavior changes during refactor
- Documentation updated if needed
- All tests pass after each phase 