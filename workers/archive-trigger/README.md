# Archive trigger (Cloudflare Worker)

Starts the forecast archive in
[`lavinoko-archive`](https://github.com/StamenchoBog/lavinoko-archive/blob/main/.github/workflows/fetch.yml) on time,
at 06:17 and 15:17 UTC (October to June) and 06:17 UTC on 1 July, 1 August and 1 September. GitHub's own schedule
starts runs hours late or drops them; a start through the API (`workflow_dispatch`) begins within seconds. GitHub's
schedule stays as the backup, so if this Worker stops, the archive still runs, only late.

The Worker has no URL. It only calls the GitHub API, with up to 3 attempts, and fails visibly in the Cloudflare
dashboard (Workers → `lavinoko-archive-trigger` → Logs) if GitHub refuses.

## Deploy (first time, or after a change here)

```sh
cd workers/archive-trigger
pnpm dlx wrangler@4.156.0 login                       # once, opens the browser
pnpm dlx wrangler@4.156.0 secret put GITHUB_TOKEN     # paste the token when asked
pnpm dlx wrangler@4.156.0 deploy
```

`GITHUB_TOKEN` is a fine-grained token: only `lavinoko-archive`, permission **Actions: read and write**, nothing
else. It is stored encrypted in Cloudflare and is never in this repository.

## Test

A deployed cron Worker cannot be started by hand, so run the same code locally against the real GitHub API:

```sh
printf 'GITHUB_TOKEN=%s\n' '<token>' > .dev.vars    # git-ignored; delete it afterwards
pnpm dlx wrangler@4.156.0 dev --test-scheduled
# in a second terminal:
curl "http://localhost:8787/__scheduled?cron=17+6,15+*+1-6,10-12+*"
rm .dev.vars
```

The wrangler log should say `Archive run started`, and a run appears under Actions in `lavinoko-archive`. It
fetches only if nothing is archived yet for the current slot. `HTTP 401` means the token is wrong; `403` or `404`
means it lacks the repository or the Actions permission.

After deploying, the dashboard (Workers → `lavinoko-archive-trigger` → Settings → Trigger events) lists both crons,
and Logs shows each invocation.

## Yearly

Before the token expires, make a new one with the same settings and run `secret put GITHUB_TOKEN` again.
