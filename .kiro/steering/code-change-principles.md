---
inclusion: always
---

# Code Change Principles

All code modifications (bug fixes, features, refactoring) must follow this workflow.

## Before Changes: Validate Understanding

- **Features**: Confirm requirements are clear with well-defined scope. Ask for clarification before starting if anything is ambiguous.
- **Bugs**: Read the relevant code first. Verify the issue exists and is reproducible. Never modify code based on assumptions.

## During Changes: Minimize Impact

- Bug fixes must not break existing functionality or introduce new issues.
- Keep changes minimal — only modify code directly related to the task.
- If changes may affect other modules, explain the impact scope before proceeding.

## After Changes: Verify and Review

- Run the project's build/compile step to confirm no errors.
- Review changes for correctness, completeness, and security risks.
- If verification fails, continue fixing until all checks pass — do not submit broken code.
- If two different approaches fail verification, stop and discuss alternatives with the user.
