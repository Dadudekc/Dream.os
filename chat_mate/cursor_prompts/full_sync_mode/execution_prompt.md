# ⚡ EXECUTION MODE: FULL SYNC MODE

## Role
Execute task rapidly, precision + convergence priority.

## Constraints
- Follow Cursor Rules v1.0
- No architecture decisions
- Provide Git commit message after each task
- Explain tradeoffs briefly before major refactors

## Git Branch & Commit Rules
- Branch prefix: `feature/cursor-[task-name]`
- Commit format: `"Feature: [task description]. Next: [next step]."`

## Example Task Format
```
TASK: [Task description]
MODE: FULL SYNC MODE
CONSTRAINTS:
- No architectural changes
- Provide commit message and tradeoffs
```

## Execution Flow
1. Create feature branch
2. Execute task with precision
3. Document tradeoffs if needed
4. Commit changes
5. Push to remote

## Git Commands
```bash
git checkout -b feature/cursor-[task-name]
# ... execute task ...
git add .
git commit -m "Feature: [task description]. Next: [next step]."
git push origin feature/cursor-[task-name]
```

## Quality Checks
- Code follows project style guide
- No architectural changes
- All tests pass
- Documentation updated if needed 