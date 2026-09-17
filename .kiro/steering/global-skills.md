---
inclusion: always
---

# Global Skills Location

User-defined global skills are available at `~/.agents/skills/`. Each subdirectory contains a skill that can be referenced or loaded when needed.

## Skill Usage Rules

1. **Proactive Usage**: When working on any task, proactively evaluate whether a global skill could help. If a skill's purpose matches the current task (e.g., `diagnosing-bugs` for debugging, `writing-clearly-and-concisely` for documentation), load and apply it without waiting for the user to explicitly request it.

2. **User Reference**: When the user mentions a skill by name, check this directory for matching skill definitions.

3. **Skill Discovery**: At the start of complex tasks, briefly scan available skills in `~/.agents/skills/` to identify relevant ones.
