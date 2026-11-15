# Security policy

Project LavinOko builds a free public site about mountain weather and avalanche terrain in North Macedonia
("Лавински информации / Avalanche information"). People may plan trips with it, so we treat two kinds of problems as
urgent: **security** vulnerabilities and **safety** problems.

## Supported versions

| Version | Supported |
|---|---|
| `main` branch and the site built from it | Yes |
| Older commits, forks, local copies | No |

There are no versioned releases yet; fixes go to `main`.

## Reporting a vulnerability

Report privately through GitHub: **[Report a vulnerability](https://github.com/StamenchoBog/lavinoko/security/advisories/new)**
(Security tab → "Report a vulnerability"). Only the maintainers can see the report.

Do not open a public issue, pull request or discussion about a vulnerability before it is fixed and disclosed.

Please include:
- what is affected (file, page, workflow, data file) and which commit or date
- steps to reproduce, or a proof of concept
- what an attacker could do, and who would be affected
- a suggested fix, if you have one

Reports in Macedonian, Albanian or English are welcome.

## Scope

**Security vulnerabilities**, for example:
- code running in a visitor's browser that should not (cross-site scripting, unsafe map or attribution content)
- a way to change the published data, the forecast archive
  ([lavinoko-archive](https://github.com/StamenchoBog/lavinoko-archive)) or the site without permission
- weaknesses in the GitHub Actions workflows (token misuse, injection, untrusted code running with write access)
- a compromised or malicious dependency
- leaking personal data

**Safety problems**, for example:
- the site showing a danger rating, or anything that reads as "safe", where it should show only weather
- forecast values, alerts or terrain classes that are clearly wrong in a way that could lead someone into
  avalanche terrain
- a printed or offline page that loses the "not an avalanche danger rating" notice

Report safety problems the same private way if they are serious or easy to exploit; otherwise a normal issue is fine.

**Out of scope:** forecast accuracy in general (the weather models were simply wrong). Those reports are welcome as
issues and feed the forecast verification. Vulnerabilities in third-party services (Open-Meteo, Copernicus,
OpenStreetMap tile hosts, GitHub) go to those services.

## What to expect

This is a volunteer project. We aim to:
- acknowledge a report within **7 days**
- confirm or reject it, with reasons, within **14 days**
- fix or mitigate a confirmed problem within **30 days**, sooner for anything critical, and keep you informed

## Disclosure policy

We follow coordinated disclosure:
1. The report stays private while we confirm and fix it, working with you in the private advisory.
2. Once the fix is on `main` (and the site, when hosted), we publish a
   [GitHub security advisory](https://github.com/StamenchoBog/lavinoko/security/advisories) describing the problem,
   the affected versions and the fix, and request a CVE through GitHub where the problem warrants one.
3. We credit the reporter in the advisory, unless they prefer not to be named.

We ask reporters not to disclose publicly until the advisory is published, or **90 days** after the report,
whichever comes first. If a fix needs longer, we will agree a new date with you. If a problem is already being
exploited, we may publish sooner.

## Safe harbor

Good-faith research that follows these rules is welcome, and we will not take legal or other action against it:
- test against your own local copy (see README), not the public site, where possible
- do not access, change or delete other people's data, and stop as soon as you reach data that is not yours
- do not run load or denial-of-service tests
- do not test third-party services the project uses
- give us reasonable time to fix the problem before disclosing it (see "Disclosure policy")

## How the project protects itself

- Dependencies: Dependabot, a 7-day minimum release age, and no install scripts unless reviewed
  (`frontend/pnpm-workspace.yaml`); GitHub Actions pinned to full commit SHAs.
- Workflows run with read-only tokens by default; only the archive job writes, and only to the archive repository.
- The forecast and terrain files the site loads are checked against a schema before use (`backend/contract/`).
- Repository settings and branch rules: [docs/repository-settings.md](docs/repository-settings.md).
