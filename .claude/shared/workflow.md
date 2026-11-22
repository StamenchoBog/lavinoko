# Workflow

How a change goes from idea to `main` in LavinOko. It builds on the spec → plan → task flow already used in
`docs/superpowers/`, and adds a threat model up front and four review passes at the end. Each step names the
sub-agent in `.claude/agents/` that does it.

Small fixes (a typo, one-line bug, dependency bump with a green CI) skip steps 1–3: implement, run the checks,
then run only the reviewers whose area the diff touches.

## 1. Spec

Talk the change through with the user and write `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`:
Intent, Goals, Non-goals, Anti-goals, Approaches considered (with the chosen one marked), and open questions.
The user approves it (`**Status:** approved`) before anything else happens.

## 2. Threat model — `threat-modeler`

Run it on the approved spec when the change touches any of:
- data the site loads (`frontend/static/data/`, `backend/contract/`), or anything fetched from outside
  (Open-Meteo, Copernicus, tiles, the archive);
- GitHub Actions, the archive workflow, the Cloudflare Worker, tokens or secrets;
- dependencies, `pnpm-workspace.yaml`, `pyproject.toml`, install scripts;
- the service worker / offline cache;
- **safety wording**: alerts, levels, "no snow" / "favourable" text, print output, anything a person might read
  as a danger rating or as "safe".

Its findings go into the plan's **Global Constraints** and **Review Focus**, each with the test that covers it.

## 3. Plan

Write `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` in the existing format: Goal, Architecture, Tech Stack,
Spec link, Global Constraints, Review Focus, then numbered Tasks. Each task lists Files (create / modify / test),
Interfaces it produces, and checkbox steps: write the failing test, run it (expect FAIL), implement, run the
checks (expect PASS). The user approves the plan.

## 4. Implement — `implementer`

One `implementer` run per task, in order. Give it the plan path and the task number. It works test-first, stays
inside the task's files, and ends each task with the checks below passing. It does not commit.

## 5. Simplify — `code-simplifier`

On the whole diff once all tasks are done. Behaviour-preserving clean-up only; checks must still pass.

## 6. Review

Run these in parallel on the diff (`git diff main...` or the working tree):

| Reviewer | Run when |
|---|---|
| `pattern-reviewer` | always |
| `security-code-reviewer` | always (it says "nothing to report" quickly for pure UI text changes) |
| `ui-design-reviewer` | anything under `frontend/src/` that renders, `i18n.ts`, print, or tokens |

Each reports findings ranked most severe first, with file:line and a concrete failure scenario. They do not edit.
The main session fixes what is confirmed (or sends it back to `implementer`), re-runs the checks, and repeats the
reviewer that raised it.

## 7. Hand over

Summarise what changed, which checks ran and their results, and anything skipped. **The user commits** unless they
ask otherwise. Update `README.md` / `docs/architecture/README.md` when behaviour or layout described there changed.

## Checks

Run what the change touches; CI (`.github/workflows/ci.yml`) runs all of them.

```sh
# backend/
uv run --only-group lint ruff check . && uv run --only-group lint ruff format --check .
uv run --group dev pytest -q
uv run python -m contract.generate --check      # after editing contract/models.py, run without --check

# frontend/
pnpm lint && pnpm check                         # check fails on warnings
pnpm build && pnpm size                         # first load < 100 KB gzipped
pnpm test:data                                  # if static/data/ is empty
pnpm exec playwright test --project=unit --trace off
pnpm exec playwright test --project=e2e --trace off
```

## Rules every step keeps

- Not an avalanche danger rating: nothing reads as "safe" or as a rating; the notice stays wherever it is today.
- Macedonian and English strings for every new text (`frontend/src/lib/i18n.ts`), Macedonian first.
- The data contract has one source, `backend/contract/models.py`; generated files are never edited by hand.
- Print and map code stay lazy; the 100 KB first-load budget holds.
- WCAG AAA text contrast (7:1) for snow glare; symbols 3:1; meaning never by colour alone.
- Dependencies: exact versions, 7-day release age, no unreviewed install scripts, Actions pinned to SHAs.
- Plain, short English in docs and comments; say why, not what.
