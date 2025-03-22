# 🛠️ EXECUTION MODE: RED-GREEN-REFACTOR MODE

## Role
Strict test-driven development with enforced phases.

## Constraints
- Red phase: Write a failing test first
- Green phase: Make the test pass
- Refactor phase: Optimize code without altering behavior
- All phases must complete in order
- Provide Git commit message after each cycle

## Git Branch & Commit Rules
- Branch prefix: `refactor/cursor-[task-name]`
- Commit format: `"Refactor: [task description]. Tests [status]. Next: [next step]."`

## Example Task Format
```
TASK: [Task description]
MODE: RED-GREEN-REFACTOR MODE
CONSTRAINTS:
- Red → Green → Refactor phases required
- No core/bootstrap changes
- Provide commit message after test pass + refactor
```

## Execution Flow
1. Create refactor branch
2. Red Phase:
   - Write failing test
   - Commit with "Red: [test description]"
3. Green Phase:
   - Make test pass
   - Commit with "Green: [implementation]"
4. Refactor Phase:
   - Optimize code
   - Commit with "Refactor: [optimizations]"
5. Push to remote

## Git Commands
```bash
git checkout -b refactor/cursor-[task-name]

# Red Phase
git add .
git commit -m "Red: [test description]"

# Green Phase
git add .
git commit -m "Green: [implementation]"

# Refactor Phase
git add .
git commit -m "Refactor: [optimizations]"

git push origin refactor/cursor-[task-name]
```

## Quality Checks
- Tests are meaningful and cover edge cases
- Code follows project style guide
- No behavior changes during refactor
- Documentation updated if needed
- All tests pass after each phase 