# SMS Broadcast for Home Assistant — 1.0.1

Custom integration with UI setup, `smsbroadcast.send_sms` and a credit balance sensor.
Community custom integration maintained by [x86digital](https://github.com/x86digital). It is not affiliated with SMS Broadcast or an official Home Assistant core integration.

Requires Home Assistant 2025.3 or newer. The minimum is an API compatibility floor; live compatibility testing is still required.

## Install through HACS

1. Open HACS, select the three-dot menu, then **Custom repositories**.
2. Add `https://github.com/x86digital/ha-smsbroadcast` with type **Integration**.
3. Find **SMS Broadcast** in HACS and download it.
4. Restart Home Assistant fully.
5. Go to **Settings → Devices & services → Add integration → SMS Broadcast**.
6. Enter your own username, password and sender ID. Setup checks your balance without sending an SMS.

This repository must be published before the above URL works. Catalogue listing is a separate review; adding this custom repository does not require that listing.

## Install manually

1. Extract this ZIP on your computer.
2. Copy the `smsbroadcast` folder from `custom_components` into your Home Assistant config directory's `custom_components` folder. Create `custom_components` if needed.
3. The final path must be `/config/custom_components/smsbroadcast/manifest.json` on Home Assistant OS. On Container installations, use the folder mounted as `/config`.
4. Restart Home Assistant fully, then go to **Settings → Devices & services → Add integration** and search for **SMS Broadcast**. If it does not appear, refresh the browser and check the Home Assistant logs.
5. Enter your SMS Broadcast username and password. The sender defaults to blank, using SMS Broadcast's two-way number. Enter your own approved sender ID if required; it must be permitted for your account.
6. Setup checks your credit balance; it does not send a test SMS. Once added, look for the **SMS Broadcast Credit balance** sensor.

One account is supported. Credentials are held in Home Assistant's config entry, not in automations. Treat Home Assistant configuration and backups as sensitive; config-entry storage is not a secrets vault. The integration sends credentials only in an HTTPS POST body and never intentionally logs credentials, message text or raw provider responses.

## Send a test SMS

Open **Developer tools → Actions**, switch to YAML and run this after replacing the example number with your own:

```yaml
action: smsbroadcast.send_sms
data:
  to: "0412345678"
  message: "Home Assistant SMS Broadcast test."
```

This action sends a real, chargeable SMS. An accepted action means the provider accepted it, not that the handset received it. Delivery receipts and inbound messages are not included in this version.

## Migrate an existing REST action

Before:

```yaml
action: rest_command.sms_request
data:
  mobilenumber: "0412345678"
  message: "Power failure detected."
```

After:

```yaml
action: smsbroadcast.send_sms
data:
  to: "0412345678"
  message: "Power failure detected."
```

The recipient field changes from `mobilenumber` to `to`. Message templates continue to work. After updating and testing all callers, remove only the old `sms_request` definition from `rest_command`, retaining other REST commands. If this leaves `rest_command` empty, remove that empty block as well, then restart Home Assistant.

## Multiple recipients and optional fields

```yaml
action: smsbroadcast.send_sms
data:
  to:
    - "0412345678"
    - "0498765432"
  message: >-
    ALERT: Home alarm triggered at
    {{ now().strftime('%H:%M:%S') }}.
  reference: "home-alarm"
  delay: 0
  maxsplit: 5
```

`to` accepts one quoted number, comma-separated quoted numbers, or a list of quoted numbers. Australian 04 numbers are converted to 614 format; spaces, parentheses, hyphens and a leading + are handled. Duplicate normalized numbers are removed within one action. The provider remains responsible for determining whether each number is valid.

`sender` optionally overrides the configured sender. Omit it to use your default; an explicit empty string uses the provider's two-way number. `reference` is optional and at most 20 characters; `delay` is a nonnegative integer number of minutes. `maxsplit` is 1–5, default 5; maximum documented length is 160 characters for 1 part or 153 × maxsplit for multiple parts, up to 765. Long messages cost multiple credits per recipient. Unicode and extended characters may change the provider's encoding/credit calculation; the provider enforces its actual limits.

## Balance and settings

Balance refreshes hourly and after an accepted send response. A zero balance remains a valid sensor reading. A balance failure makes the sensor unavailable; it does not cause an already accepted send to be reported as failed. You can request a refresh with Home Assistant's **Update entity** action on the balance sensor.

Open the integration's **Configure** menu to change the default sender and maximum parts. If credentials are rejected, Home Assistant starts a reauthentication flow to update the password. To change the account username, remove and re-add the integration.

## Errors and duplicate prevention

The API can accept valid recipients while rejecting others in the same action. For a partial failure, the action error reports how many were accepted and lists rejected numbers. Check the portal and resend only to rejected recipients. Avoid wrapping this action in blanket retries.

No automatic send retries are performed. If sending times out, gets an HTTP error, or returns malformed/incomplete data, it may already have been accepted. Check the SMS Broadcast portal before resending. No callbacks/webhooks are installed and no external access to Home Assistant is needed.

Actions support optional response data in scripts:

```yaml
- action: smsbroadcast.send_sms
  data:
    to: "0412345678"
    message: "Power failure detected."
  response_variable: sms_result
```

`sms_result.accepted` contains a list of `{to, sms_reference}` objects. Normal automations do not need `response_variable`.

## Validation

Offline API tests cover balance parsing, authentication failures, successful/partial/malformed send responses, number handling, special characters in POST data, message limits, HTTP failures and timeouts without retries. Run with Python and aiohttp installed:

```sh
python3 -m unittest discover -s tests -v
```

Python syntax and JSON files were also checked. This package has not been loaded on a live Home Assistant instance or tested with live SMS Broadcast credentials. Designed for current Home Assistant versions using config entry runtime data; update an older installation if unsupported Home Assistant APIs appear in the logs.

## API reference

SMS Broadcast official Advanced HTTP API:
https://smsbroadcast.com.au/wp-content/uploads/2023/01/Advanced-HTTP-API.pdf

Home Assistant configuration flows and service actions:
https://developers.home-assistant.io/docs/core/integration/config_flow/
https://developers.home-assistant.io/docs/dev_101_services/

## Updating

Update through HACS, then restart Home Assistant. Manual installations can replace the `custom_components/smsbroadcast` folder and restart. Existing config entries keep their chosen sender; the blank default only applies to new setup.

## Support and contributing

Report issues at https://github.com/x86digital/ha-smsbroadcast/issues with your Home Assistant version and a redacted error message. Never include credentials, unredacted backups, message content or personal mobile numbers. For account/sender approval problems, contact SMS Broadcast.

Development and publication steps are in [PUBLISHING.md](PUBLISHING.md). Licensed under MIT; see [LICENSE](LICENSE).
