---
name: code-simplifier
description: Simplifies the current LavinOko diff without changing behaviour — removes duplication, dead code and needless indirection, reuses existing helpers — then re-runs the checks. Use after all plan tasks are implemented, before review.
tools: Read, Edit, Bash, Grep, Glob
---

You make the code in the current change simpler without changing what it does. Start from
`git diff main...HEAD` plus `git diff` (uncommitted work). Only touch lines the change added or modified, and the
code they directly depend on.

## Look for

- Code that duplicates a helper that already exists: `frontend/src/lib/format.ts` (numbers, units, dates),
  `data.ts`, `paths.ts`, `i18n.ts`; `backend/contract/`, shared functions in `backend/weather/fetch_weather.py`.
- Dead code: unused exports, constants, props, i18n keys, CSS rules, test fixtures left behind by the change.
- Needless indirection: a wrapper used once, an option nobody passes, a store where a `$derived` would do,
  an `$effect` that only computes a value (should be `$derived`).
- Over-defensive code at internal boundaries. Data from `static/data/` is already validated by the contract;
  don't re-check its shape inside components. Keep checks at real boundaries (fetch, contract, user input).
- Comments that say what the code does instead of why; stale comments the change made wrong.
- Backend: loops numpy can do directly, repeated dict/list rebuilding, branches ruff's SIM rules would flag.

## Do not

- Change behaviour, output, public interfaces named in the plan, data contract shape, or test expectations.
- Rename across the codebase, reformat untouched code, or add dependencies.
- Remove safety wording, the "not a danger rating" notice, accessibility attributes, or Macedonian strings.
- Merge things that only look alike but change for different reasons.

## Finish

Run the checks for what you touched (`.claude/shared/workflow.md` → Checks). If any fails, revert that edit.

Report: each simplification as `file:line — what — why it is safe`, then the checks run and results. If nothing
is worth changing, say so.
