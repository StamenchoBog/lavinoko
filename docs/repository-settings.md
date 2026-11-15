# Repository settings

GitHub settings that are not stored in the code. Kept here so they can be checked and repeated.
Checked items are confirmed set; tick the rest as you set them.

## Now: one maintainer

### `lavinoko` (code)

**Settings → General**
- [ ] Features: Issues on; Wiki off (docs live in the repo); Discussions off until there is a community to use them.
- [ ] Pull requests: allow **squash merging** only; "Automatically delete head branches" on.
- [ ] "Always suggest updating pull request branches" on.

**Settings → Rules → Rulesets → New branch ruleset** "main", target: default branch, enforcement: active
- [ ] Restrict deletions
- [ ] Block force pushes
- [ ] Require status checks to pass: **`CI passed`** (the one stable check in `ci.yml`; the matrix jobs behind it may change)
- [ ] Require linear history
- [ ] Bypass list: Repository admin, **"For pull requests only"**. You can still merge your own PR when needed, but
      never push broken code straight to `main`.

Why not "require a pull request" yet: alone, every change would need a PR you approve yourself. Pushing to a branch
and merging through a PR is still the recommended habit: CI runs before the change lands.

**Settings → Code security**
- [ ] Private vulnerability reporting: **on** (SECURITY.md links to it)
- [ ] Dependency graph: on
- [ ] Dependabot alerts: on
- [ ] Dependabot security updates: on (they ignore the 7-day cooldown; see "Security fixes" below)
- [ ] Grouped security updates: on
- [ ] Code scanning → CodeQL → **Default setup** (free for public repos; JavaScript/TypeScript, Python, Actions)
- [ ] Secret scanning and push protection: on

**Settings → Actions → General**
- [ ] Actions permissions: "Allow StamenchoBog, and select non-StamenchoBog, actions and reusable workflows", allow
      actions created by GitHub, and add: `astral-sh/setup-uv@*`, `pnpm/action-setup@*`
      (every workflow already pins them to a commit)
- [ ] Require actions to be pinned to a full-length commit SHA: on
- [ ] Workflow permissions: **Read repository contents** (the default token is read-only; jobs ask for more themselves)
- [ ] "Allow GitHub Actions to create and approve pull requests": off
- [ ] Fork pull request workflows: "Require approval for first-time contributors"

**Settings → Branches / Tags**
- [ ] Tag ruleset for `v*` (when releases start): restrict deletions and updates.

### `lavinoko-archive` (data)

The schedule commits straight to `main` with the workflow token, so **do not require pull requests or status checks**
there; that would stop the archive.
- [ ] Ruleset on `main`: restrict deletions, block force pushes. Nothing else.
- [ ] Settings → Actions → Workflow permissions: read and write (needed for the commit); "create and approve pull
      requests" off.
- [ ] Issues and wiki off; point people to `lavinoko` instead.

### Your account
- [ ] Two-factor authentication with a security key or passkey.
- [ ] Commit signing (SSH or GPG key) registered on GitHub, so commits show "Verified".
- [ ] Notifications: Actions failures on, so missed or failed archive runs reach you by e-mail.

## Yearly: `security.txt`

`frontend/static/.well-known/security.txt` (RFC 9116) must not expire. Before **2027-11-15**, move `Expires` a year
ahead. When the site gets its domain, add `Canonical: https://<domain>/.well-known/security.txt`.

## Security fixes that are newer than 7 days

`frontend/pnpm-workspace.yaml` refuses packages published less than 7 days ago. For an urgent fix in a Dependabot
security PR, add only that version to `minimumReleaseAgeExclude` in the same PR, e.g.:

```yaml
minimumReleaseAgeExclude:
  - maplibre-gl@6.17.1
```

Remove the entry once the version is older than 7 days.

## Later: when others join

- **Organisation**: move both repositories to a GitHub organisation (e.g. the registered association). Use teams
  (`@org/maintainers`, `@org/forecasters`) in `.github/CODEOWNERS` instead of personal names.
- **Ruleset on `main`**: add "Require a pull request before merging" with 1 approval, "Require review from Code
  Owners", "Dismiss stale approvals when new commits are pushed" and "Require conversation resolution". Keep the
  admin bypass for emergencies only.
- **Safety wording** (`frontend/src/lib/i18n.ts`, place view) and alert thresholds (`backend/weather/`) get a
  forecaster as code owner before any danger rating is published (a shadow season, winter 2028/29 at the earliest).
- **Deployment**: when the site is hosted, deploy from a GitHub Actions *environment* ("production") with required
  reviewers, its own secrets, and deployment only from `main`.
- **Signed commits**: "Require signed commits" in the ruleset once every contributor signs.
- **Contributing guide**: add `CONTRIBUTING.md` (setup, checks, language rules for safety text) when the first
  outside contributor arrives.
