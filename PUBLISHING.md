# Publish x86digital/ha-smsbroadcast

The package is prepared for this repository. It has not been published or accepted into HACS.

## Create the public repository

Sign in as x86digital and create a public repository named **ha-smsbroadcast** at https://github.com/new. Description: **SMS Broadcast SMS sending and credit balance for Home Assistant**. Leave the initial README, licence and gitignore options unchecked; this package includes them.

Extract the repository ZIP. Open PowerShell or a terminal inside the extracted `ha-smsbroadcast` folder containing `hacs.json` and `custom_components`. If Git is installed:

```sh
git init -b main
git add .
git commit -m "Prepare SMS Broadcast community integration"
git remote add origin https://github.com/x86digital/ha-smsbroadcast.git
git push -u origin main
```

Git will use your normal GitHub authentication. Do not paste access tokens into chat or commit them. If Git asks for a commit author, configure your own name and GitHub email before committing.

Add repository topics under the About settings: `home-assistant`, `hacs`, `sms`, `smsbroadcast`, `custom-integration`. If the repository already exists, inspect it before uploading; do not overwrite unrelated content.

Browser upload alternative: upload the **contents** of the extracted folder to the repository root, including `.github/workflows/validate.yaml`. Do not upload only the ZIP or nest the files inside a second `ha-smsbroadcast` folder. If the browser omits `.github`, create `.github/workflows/validate.yaml` separately with the supplied contents.

## Validate before the first release

1. Check the Actions tab. API tests, hassfest and HACS validation must pass. The HACS job temporarily ignores the brands check only; that is not catalogue approval.
2. Install on a live Home Assistant instance. Confirm UI setup and the balance sensor.
3. Send one test SMS to your own phone. Confirm the sender and received text; this costs credits.
4. Test an automation, restart persistence, settings changes and unloading/reloading. Do not deliberately bulk-send or test malformed recipient sends on the paid API.
5. Record tested Home Assistant versions in the README. The 2025.3 API floor has not been tested as a version matrix.

## Release

When checks and the live test pass, open **Releases → Draft a new release**. Create tag **v1.0.1** from `main` and title **SMS Broadcast 1.0.1**. Use the 1.0.1 changelog as the description. Publish the release. No custom release ZIP is needed: HACS installs `custom_components/smsbroadcast` from the tagged source.

For later releases, update `manifest.json`'s version and the changelog, validate, then publish a matching tag/release.

Users can now add https://github.com/x86digital/ha-smsbroadcast as a HACS custom repository of type Integration.

## HACS catalogue submission is separate

Follow https://hacs.dev/docs/publish/include/ and https://hacs.dev/docs/publish/integration/. Add the required brand assets to home-assistant/brands through its own contribution process. Once accepted, remove `ignore: brands` from CI and make sure all HACS checks pass without ignores. Then submit the repository to the integration list in hacs/default. Catalogue inclusion depends on their review; publishing this repository does not automatically list it.
