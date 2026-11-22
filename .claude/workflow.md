## Development Workflow

### 0. Task Sizing (Choose Path First)
- **Trivial (< 20 lines, single file, no auth/data/API boundary changes):** Skip Steps 1–5. Edit directly, run tests/linters, and verify before completing.
- **Standard / Complex (multi-file, new feature, bug fix, or security/infra change):** Follow Steps 1–10 below.

---

### 1. Understand & Diagnose
- Review the request and inspect relevant code first.
- For new features: brainstorm edge cases and architecture trade-offs (use `/superpowers:brainstorming` if installed).
- For bug fixes: reproduce the failure and isolate root cause before proposing edits (use `/superpowers:systematic-debugging` if installed).

### 2. Clarify Ambiguities
- Ask concise, targeted clarifying questions on requirements, edge cases, or constraints before designing.

### 3. Plan & Threat-Model
- **A. Draft Design:** Outline the architecture, data flow, files to modify/create, and verification strategy.
- **B. Threat Model (for features touching auth, external input, network, secrets, or persistence):** Dispatch the `threat-modeler` sub-agent with *only* the draft design and project root(s)—never the full conversation history.
- **C. Fold Into Plan:** Incorporate the returned invariants table and design mitigations into the plan, turning each security invariant into an explicit verification task.

### 4. To-Do List & Checkpoints
- Only after the plan is approved, create a detailed task list with clear phase checkpoints.
- For code changes, append these mandatory review tasks at the end:
  1. Run `code-simplifier` sub-agent first and alone (mutates the diff; pass changed files + verification command).
  2. Run read-only review sub-agents in parallel:
     - `pattern-reviewer` (if `PATTERNS.md` or `patterns/` exists in the repo)
     - `security-code-reviewer` (pass changed files + plan invariants table; require `held / broken / untested` with `file:line` evidence for every row)
     - `ui-design-reviewer` (for frontend changes; optionally follow with `/impeccable critique` and `/impeccable audit`)

### 5. Implementation Strategy
- **Multi-file / multi-step tasks:** Delegate to the `implementer` sub-agent with a self-contained brief containing:
  1. Exact task goal and scope
  2. Allowed files to touch (strictly disjoint when running multiple implementers in parallel; shared files like lockfiles or registries belong to one agent only)
  3. Exact interfaces, types, and values decided in earlier steps
  4. Invariant tests this task owns
  5. Reference file in the repo whose style/structure it should mirror
  6. Exact verification command
- **Small targeted edits (< 15 lines in files already in context):** Edit directly in the main session.
- **Fix rounds:** Resume the same `implementer` agent via `SendMessage` so it retains context; spawn fresh only if context has drifted. Never use `fork` for implementation.

### 6. Implementation Rules
- Stay strictly within requested scope; follow testing conventions defined in `CLAUDE.md`.
- For frontend changes: verify visually in a headless browser if available, and apply `/impeccable polish`, `clarify`, `layout`, or `adapt` when needed.

### 7. Local Verification
- Run the project's test suite, type-checker, and linter covering the change (see `CLAUDE.md` for exact commands).
- Fix failures up to 5 rounds before escalating. If no automated check exists for a change, explicitly state that in the handoff.

### 8. Pre-Review Diff Interrogation
Before running Step 4's review sub-agents, the implementer/builder must audit the diff in this order:
1. **Unstated assumptions:** What rests on an assumption the user never asked for? Challenge it and document any necessary call under `Decisions`.
2. **Dead weight:** Delete everything added beyond the requested scope or left unused.
3. **Simplification:** Verify what becomes simpler once unused code is removed.

### 9. Infrastructure & Service Changes
- If the change adds, modifies, or removes a service, background worker, port, or deployment config, update the corresponding `CLAUDE.md`, `README.md`, `.env.example`, and deployment manifests.

### 10. Final Verification Gate
- After all review-driven edits are applied, re-run verification checks (use `/superpowers:verification-before-completion` if installed) before presenting the final summary and PR/commit readiness.