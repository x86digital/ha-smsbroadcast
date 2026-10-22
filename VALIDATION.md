# Recovery and validation

## Recovery evidence — 22 October 2026

The published `main` branch at `197c3706482971b5f9b08c8af52baa1f6137ded6` contained only the documentation/metadata and `__init__.py`. Its complete two-commit history, sole branch and advertised Git refs contained no implementation to restore; there were no pull requests.

The original saved `ha-smsbroadcast-GitHub.zip`, created 6 October 2026, was recovered. Its SHA-256 is `86d5b115e5986c87f4df562175f171cc2fc2f9527b0b1024399b483e888e11ee`. Every existing published file was byte-for-byte identical to the archive before repair. The archive contained all missing modules, services/UI metadata, the validation workflow and 16 offline API tests. These were restored rather than reconstructed.

## API verification

Checked against the provider's official [Advanced HTTP API documentation](https://smsbroadcast.com.au/wp-content/uploads/2023/01/Advanced-HTTP-API.pdf):

- HTTPS POST to `https://api.smsbroadcast.com.au/api-adv.php`; credentials in the body, no redirects.
- Balance: `action=balance`; parse `OK: <credits>`, including zero.
- Send: comma-separated `to`, `from`, `message`, optional tracking `ref`, `delay` in minutes and `maxsplit` 1–5.
- One colon-separated `OK`/`BAD` result per recipient. Valid recipients can be accepted while others fail. Authentication failure is a single `ERROR` response.
- Blank sender uses the provider's two-way number. Nonblank senders allow up to 11 alphanumeric characters and require account permission.
- Documented message limits: 160 characters for one part, 153 per part when split, maximum 765. Encoding and actual credit calculation remain provider-controlled.

No provider requests or chargeable SMS tests were made. No real credentials are used in tests.

## Repair hardening

The recovered parser checked only result count. It now checks returned recipient identities too, so repeated/mismatched response lines cannot count as a complete success. The client also normalizes/deduplicates numbers before submission and treats unreadable response bodies as communication errors. Errors do not expose raw provider bodies or credentials.

Each explicit action submits at most one POST. There are no automatic send retries or redirect replays. Deduplication applies within an action; repeated actions and restarts are not persistent idempotency protection. `reference` is a tracking field, not an idempotency key. Check the portal before retrying uncertain sends; retry only rejected recipients after partial acceptance.

## Completed offline checks

- 20 API tests, including request data, normalization/deduplication, zero/malformed balances, authentication, partial results, incorrect response recipients, message limits, timeouts and HTTP failures with one submission only.
- 14 Home Assistant lifecycle cases: setup, zero sensor, sensor unavailable/recovery, options, reauthentication, unloaded action rejection, accepted-send response, overrides, partial failure and post-send balance failures. All provider calls are mocked and network sockets are disabled.
- Full suite: **34 passed** on Home Assistant **2025.3.4 / Python 3.13** and **2026.10.2 / Python 3.14**.
- Python compilation, required package files, JSON/YAML structure, matching English UI text and Ruff checks.

The restored GitHub workflow also runs hassfest and HACS checks. Their remote results are visible on the repository's Actions tab. HACS brand validation is explicitly deferred; repository topics must be present for its metadata check. Neither CI nor this report asserts catalogue approval.

## Remaining live checks

A live Home Assistant installation and SMS Broadcast account are still required to verify real authentication, account balance, sender approval, one approved chargeable SMS/handset receipt, automation behaviour, restart persistence and UI operation. Follow [PUBLISHING.md](PUBLISHING.md). No release is published by this repair because those checks remain outstanding.
