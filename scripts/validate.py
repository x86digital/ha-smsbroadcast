"""Fast offline package validation. No accounts, sockets or SMS required."""

import ast
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "smsbroadcast"
REQUIRED = [
    "__init__.py",
    "api.py",
    "const.py",
    "coordinator.py",
    "config_flow.py",
    "manifest.json",
    "sensor.py",
    "services.yaml",
    "strings.json",
    "translations/en.json",
]
for filename in REQUIRED:
    assert (COMPONENT / filename).is_file(), f"Missing integration file: {filename}"
for path in ROOT.rglob("*.py"):
    if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
        continue
    ast.parse(path.read_text(), filename=str(path))
for path in [*COMPONENT.rglob("*.json"), ROOT / "hacs.json"]:
    json.loads(path.read_text())
manifest = json.loads((COMPONENT / "manifest.json").read_text())
assert manifest["domain"] == "smsbroadcast"
assert manifest["config_flow"] is True
assert manifest["version"]
assert json.loads((COMPONENT / "strings.json").read_text()) == json.loads(
    (COMPONENT / "translations/en.json").read_text()
)
services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
assert set(services["send_sms"]["fields"]) == {
    "to",
    "message",
    "sender",
    "reference",
    "delay",
    "maxsplit",
}
workflow = yaml.safe_load((ROOT / ".github/workflows/validate.yaml").read_text())
assert {"api-tests", "home-assistant-tests", "hassfest", "hacs"} <= workflow[
    "jobs"
].keys()
print("Offline package validation passed.")
