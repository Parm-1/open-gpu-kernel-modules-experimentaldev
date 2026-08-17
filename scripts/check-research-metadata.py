#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATES = {
    "SOURCE_PRESENT", "CAPABILITY_ADVERTISED", "REQUEST_ACCEPTED",
    "AUTHENTICATED", "ENCRYPTING", "TYPE1_ACTIVE", "PROTECTED_MEMORY",
    "PROTECTED_DECODE", "PROTECTED_PRESENT", "SOFTWARE_ISOLATED",
    "HARDWARE_PROTECTED", "VENDOR_ATTESTED", "SERVICE_AUTHORIZED",
    "END_TO_END_PROVEN",
}
REQUIRED_FILES = {
    "README.md", "manifest.json", "commands.txt", "stdout.txt", "stderr.txt",
    "artifacts.sha256", "verdict.md",
}

errors: list[str] = []
for directory in sorted((ROOT / "experiments").glob("EXP-*")):
    missing = REQUIRED_FILES - {p.name for p in directory.iterdir() if p.is_file()}
    if missing:
        errors.append(f"{directory}: missing {sorted(missing)}")
        continue
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
    except Exception as exc:
        errors.append(f"{directory}: invalid manifest: {exc}")
        continue
    for key in ("schema_version", "id", "title", "question", "status", "state_claim", "source_baseline", "acceptance_criteria", "secrets_collected"):
        if key not in manifest:
            errors.append(f"{directory}: manifest missing {key}")
    if manifest.get("id") != directory.name:
        errors.append(f"{directory}: id does not match directory")
    if manifest.get("state_claim") not in ALLOWED_STATES:
        errors.append(f"{directory}: unknown state_claim {manifest.get('state_claim')!r}")
    if manifest.get("secrets_collected") is not False:
        errors.append(f"{directory}: secrets_collected must be false")

left = ROOT / "kernel-open/common/inc/nvkms-kapi.h"
right = ROOT / "src/nvidia-modeset/kapi/interface/nvkms-kapi.h"
if left.read_bytes() != right.read_bytes():
    errors.append(f"duplicate interface headers differ: {left} vs {right}")

if errors:
    print("research metadata validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("research metadata validation passed")
