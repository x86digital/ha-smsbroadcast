# Changelog

## 1.0.2

- Restore all missing integration files, UI text, action metadata, original API tests and CI workflow from the original 6 October distribution archive.
- Validate send-response recipients against the requested recipients; reject duplicate or mismatched replies as uncertain, without retries.
- Normalize and deduplicate recipients at the client boundary as well as the action boundary.
- Add offline Home Assistant lifecycle regression tests and compatibility CI for 2025.3.4 and 2026.10.2.
- Document restoration provenance, validation results and the remaining live installation/account checks.

## 1.0.1

- Prepare community distribution under x86digital/ha-smsbroadcast.
- Add HACS metadata, maintainer/issue links, MIT licence and CI validation.
- Default to a blank sender for new setups. Existing entries keep their sender.

## 1.0.0

- Initial UI setup, SMS send action and remaining credit sensor.
- Support multiple recipients, references, delays and long-message limits.
- Handle authentication, partial recipient failures and uncertain sends without automatic retries.
