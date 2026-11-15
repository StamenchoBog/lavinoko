# Security policy

Project LavinOko builds a free public site about mountain weather and avalanche terrain in North Macedonia.
People may plan trips with it, so we treat two kinds of problems as urgent: **security** problems and
**safety** problems.

## Report privately

Use GitHub's private reporting: **[Report a vulnerability](https://github.com/StamenchoBog/lavinoko/security/advisories/new)**
(Security tab → "Report a vulnerability"). Only the maintainers see the report.

Please do not open a public issue, pull request or discussion for a vulnerability until it is fixed.

Include what you can: what is affected, how to reproduce it, what an attacker could do, and any fix you suggest.
Reports in Macedonian, Albanian or English are welcome.

## What counts

**Security**, for example:
- code running in a visitor's browser that should not (cross-site scripting, unsafe map or attribution content)
- a way to change the published data, the forecast archive
  ([lavinoko-archive](https://github.com/StamenchoBog/lavinoko-archive)) or the site without permission
- weaknesses in the GitHub Actions workflows (token misuse, injection, untrusted code running with write access)
- a compromised or malicious dependency
- leaking personal data

**Safety**, for example:
- the site showing a danger rating, or anything that reads as "safe", where it should show only weather
- forecast values, alerts or terrain classes that are clearly wrong in a way that could lead someone into
  avalanche terrain
- a printed or offline page that hides the "not an avalanche danger rating" notice

Report safety problems the same private way if they are serious or easy to exploit; otherwise a normal issue is fine.

Forecast **accuracy** in general (the models were simply wrong) is not a vulnerability. Those reports are welcome
as issues, and they feed the forecast verification.

## What to expect

This is a volunteer project. We aim to:
- acknowledge a report within **7 days**
- agree on a fix or mitigation plan within **30 days** for confirmed problems, sooner for anything critical
- credit you in the advisory, if you want

Only the current `main` branch and the site built from it are supported.

## Testing rules

Good-faith research that follows these rules is welcome, and we will not take action against it:
- test against your own local copy (see README), not the public site, where possible
- do not access, change or delete other people's data
- do not run load or denial-of-service tests
- do not test the third-party services the project uses (Open-Meteo, Copernicus, OpenStreetMap tile hosts,
  GitHub); report their problems to them

## How the project protects itself

- Dependencies: Dependabot, a 7-day minimum release age, and no install scripts unless reviewed
  (`frontend/pnpm-workspace.yaml`); GitHub Actions pinned to full commit SHAs.
- Workflows run with read-only tokens by default; only the archive job writes, and only to the archive repository.
- The forecast and terrain files the site loads are checked against a schema before use (`backend/contract/`).
