# Validate and release x86digital/ha-smsbroadcast

The public repository exists. The missing implementation was recovered from the original distribution archive; see [VALIDATION.md](VALIDATION.md). Version 1.0.2 repairs the incomplete published package. A release is still gated on live installation/account checks.

## Development validation

The `.github/workflows/validate.yaml` workflow runs on pushes, pull requests and manual dispatch. It runs offline API tests, package validation, Ruff, Home Assistant lifecycle tests on 2025.3.4/Python 3.13 and 2026.10.2/Python 3.14, hassfest and HACS validation.

Local API/package checks (no account required):

```sh
python -m pip install aiohttp PyYAML ruff==0.17.1
python -m unittest discover -s tests -v
python -m compileall -q custom_components tests scripts
python scripts/validate.py
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

Home Assistant tests in an isolated Python 3.14 environment:

```sh
python -m pip install -r requirements-test.txt
python -m pytest tests -q
```

For March 2025 compatibility, use Python 3.13 and `requirements-test-baseline.txt`. Its explicit historical aiohttp pin is needed to reproduce Home Assistant 2025.3.4's dependencies; it does not pin the integration's runtime dependencies. The test suite blocks network sockets and mocks every provider request.

Add repository topics in GitHub's About settings: `home-assistant`, `hacs`, `sms`, `smsbroadcast`, `custom-integration`. HACS validates this repository metadata independently of the code. The HACS job ignores only the brands check pending the separate brand contribution; this does not confer catalogue approval.

## Live validation before release

1. Install on a live Home Assistant instance. Confirm UI setup using an account balance check, a zero balance where available, and the credit sensor. Setup does not send SMS.
2. With the account owner's approval, send one SMS to their own phone. This costs credits. Confirm the sender and received text; API acceptance alone is not delivery confirmation.
3. Test an automation, restart persistence, settings changes, manual sensor refresh and unloading/reloading. Verify password recovery when credentials require updating.
4. Check the portal after any uncertain response. Do not bulk-send or deliberately test bad recipients on the paid API, and do not wrap sends in blanket retries.
5. Record the live-tested Home Assistant version and date in the README. Offline harness coverage is not a substitute for these checks.

## Release

After automated checks and live validation pass, create a release tagged **v1.0.2** from `main`, titled **SMS Broadcast 1.0.2**, using the 1.0.2 changelog. No custom release ZIP is needed: HACS installs `custom_components/smsbroadcast` from the tagged source. Do not tag/release an untested installation as live-verified.

For future releases, update `manifest.json` and the changelog together, validate, then publish a matching tag/release. Users can add https://github.com/x86digital/ha-smsbroadcast as a HACS custom repository of type Integration.

## HACS catalogue submission

Catalogue inclusion is separate from custom-repository installation. Follow https://hacs.xyz/docs/publish/include/ and https://hacs.xyz/docs/publish/integration/. Contribute brand assets to home-assistant/brands, then remove `ignore: brands` from CI when accepted. Submit the repository to hacs/default only after all catalogue requirements are met.
