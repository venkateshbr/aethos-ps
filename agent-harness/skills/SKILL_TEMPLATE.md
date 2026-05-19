---
name: example-skill
description: Use this skill when <trigger condition>. It provides <capability> and requires <verification>.
---

# Skill Name

Use this skill when the task matches the description above.

## Required Context

- Read the project context file.
- Read any domain/design/test/security docs relevant to this skill.
- Inspect existing code before changing patterns.

## Workflow

1. Confirm scope and issue.
2. Load only the necessary context.
3. Identify local patterns.
4. Implement using the smallest safe change.
5. Verify with the commands below.
6. Report what changed and what remains.

## Must Do

- Follow project architecture.
- Avoid secrets and unrelated refactors.
- Prefer repo-native helpers.

## Avoid

- Duplicating existing abstractions.
- Hardcoding project-specific values in generic code.
- Claiming acceptance without real evidence.

## Verification

```bash
<project-specific verification command>
```

