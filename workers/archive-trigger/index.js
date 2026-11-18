// Starts the forecast archive on time. GitHub's own schedule starts runs hours late or drops them; a
// workflow_dispatch through the API starts within seconds. GitHub's schedule stays as the backup.
//
// Only a scheduled handler: the Worker has no URL and answers no requests (wrangler.jsonc).
// Secret GITHUB_TOKEN: fine-grained token, only lavinoko-archive, Actions: read and write.

const DISPATCH_URL =
  "https://api.github.com/repos/StamenchoBog/lavinoko-archive/actions/workflows/fetch.yml/dispatches";

export default {
  async scheduled(controller, env) {
    // A pasted secret often carries a line break, spaces or a "Bearer " prefix; GitHub then answers 401.
    const raw = String(env.GITHUB_TOKEN ?? "");
    const token = raw.trim().replace(/^Bearer\s+/i, "");
    if (!token) {
      throw new Error("GITHUB_TOKEN is not set: add it under Settings → Variables and Secrets as type Secret");
    }
    // only_if_missing: a second start in the same slot (a retry here, a GitHub backup) does nothing.
    const body = JSON.stringify({ ref: "main", inputs: { only_if_missing: "true" } });
    let last = "";
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const res = await fetch(DISPATCH_URL, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lavinoko-archive-trigger", // GitHub refuses requests without one
          },
          body,
        });
        if (res.status === 204) {
          console.log(`Archive run started (cron "${controller.cron}", attempt ${attempt})`);
          return;
        }
        last = `HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`;
        if (res.status === 401) {
          // Which token does Cloudflare hold? Compare with your copy; never logs the token itself.
          last +=
            ` | GITHUB_TOKEN: ${token.length} chars, starts with "${token.slice(0, 11)}", ends with` +
            ` "…${token.slice(-4)}"${raw !== token ? ", had spaces, line breaks or Bearer (removed)" : ""}`;
        }
        // 401/403/404/422: token or setup is wrong; retrying will not help.
        if (res.status < 500 && res.status !== 429) break;
      } catch (err) {
        last = String(err);
      }
      await new Promise((r) => setTimeout(r, attempt * 10_000));
    }
    // Thrown, so the invocation shows as failed in the Cloudflare dashboard.
    throw new Error(`Could not start the archive run: ${last}`);
  },
};
