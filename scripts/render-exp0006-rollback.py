#!/usr/bin/env python3
"""Render a non-executing, machine-specific EXP-0006 rollback plan."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

REQUIRED_MODULES = ("nvidia", "nvidia_modeset", "nvidia_drm")
OPTIONAL_MODULES = ("nvidia_uvm", "nvidia_peermem")
ALL_MODULES = REQUIRED_MODULES + OPTIONAL_MODULES


def module_by_name(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for item in snapshot.get("modules", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            records[name] = item
    return records


def valid_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = snapshot.get("expected_version")
    if not isinstance(expected, str) or not expected:
        errors.append("missing expected_version")
    if not snapshot.get("kernel_release"):
        errors.append("missing kernel_release")

    records = module_by_name(snapshot)
    for name in REQUIRED_MODULES:
        record = records.get(name)
        if record is None:
            errors.append(f"missing module record: {name}")
            continue
        if record.get("loaded") is not True:
            errors.append(f"{name}: was not loaded in the known-good snapshot")
        for field in ("filename", "version", "vermagic"):
            if not record.get(field):
                errors.append(f"{name}: missing {field}")
        if not valid_sha256(record.get("sha256")):
            errors.append(f"{name}: invalid or missing sha256")
        if expected and record.get("version") != expected:
            errors.append(f"{name}: version does not match expected_version")

    for name in OPTIONAL_MODULES:
        record = records.get(name)
        if not record or record.get("loaded") is not True:
            continue
        for field in ("filename", "version", "vermagic"):
            if not record.get(field):
                errors.append(f"{name}: loaded but missing {field}")
        if not valid_sha256(record.get("sha256")):
            errors.append(f"{name}: loaded but has invalid or missing sha256")
        if expected and record.get("version") != expected:
            errors.append(f"{name}: loaded version does not match expected_version")
    return errors


def shell_test_module(name: str, record: dict[str, Any]) -> list[str]:
    quoted_name = shlex.quote(name)
    expected_path = shlex.quote(str(record["filename"]))
    expected_hash = shlex.quote(str(record["sha256"]))
    expected_version = shlex.quote(str(record["version"]))
    expected_vermagic = shlex.quote(str(record["vermagic"]))
    return [
        f"test -d /sys/module/{quoted_name}",
        f"test \"$(modinfo -n {quoted_name})\" = {expected_path}",
        f"test \"$(sha256sum \"$(modinfo -n {quoted_name})\" | awk '{{print $1}}')\" = {expected_hash}",
        f"test \"$(modinfo -F version {quoted_name})\" = {expected_version}",
        f"test \"$(modinfo -F vermagic {quoted_name})\" = {expected_vermagic}",
    ]


def render(snapshot: dict[str, Any]) -> str:
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("invalid snapshot: " + "; ".join(errors))

    records = module_by_name(snapshot)
    expected = str(snapshot["expected_version"])
    kernel_release = str(snapshot["kernel_release"])
    loaded_modules = [name for name in ALL_MODULES if records.get(name, {}).get("loaded")]
    load_order = [
        "nvidia",
        "nvidia_modeset",
        *[name for name in OPTIONAL_MODULES if name in loaded_modules],
        "nvidia_drm",
    ]
    parameters = snapshot.get("nvidia_drm_parameters")
    if not isinstance(parameters, dict):
        parameters = {}

    lines = [
        "# EXP-0006 machine-specific rollback plan",
        "",
        "> This document does not execute anything. Review it offline before module-load approval.",
        "",
        f"Expected known-good NVIDIA version: `{expected}`",
        f"Expected kernel release: `{kernel_release}`",
        "",
        "## Known-good module identity",
        "",
        "| Module | Loaded at snapshot | Path | SHA-256 | Version | Vermagic |",
        "|---|---:|---|---|---|---|",
    ]
    for name in ALL_MODULES:
        record = records.get(name)
        if record is None:
            continue
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                name,
                "yes" if record.get("loaded") else "no",
                record.get("filename") or "unavailable",
                record.get("sha256") or "unavailable",
                record.get("version") or "unavailable",
                record.get("vermagic") or "unavailable",
            )
        )

    lines.extend(
        [
            "",
            "## Intended recovery sequence",
            "",
            "Run only from working SSH or local TTY after the graphical session is stopped. Never use force-removal.",
            "",
            "```bash",
            "set -euo pipefail",
            f"test \"$(uname -r)\" = {shlex.quote(kernel_release)}",
            "sudo systemctl isolate multi-user.target",
            "",
            "unload_nvidia_stack() {",
            "  local module",
            "  for module in nvidia_drm nvidia_modeset nvidia_uvm nvidia_peermem nvidia; do",
            "    if [[ -d \"/sys/module/$module\" ]]; then",
            "      sudo modprobe -r \"$module\"",
            "    fi",
            "  done",
            "  for module in nvidia_drm nvidia_modeset nvidia_uvm nvidia_peermem nvidia; do",
            "    if [[ -d \"/sys/module/$module\" ]]; then",
            "      echo \"FAIL: $module is still loaded\" >&2",
            "      return 1",
            "    fi",
            "  done",
            "}",
            "unload_nvidia_stack",
            "",
        ]
    )
    for name in load_order:
        lines.append("sudo modprobe " + shlex.quote(name))

    lines.extend(
        [
            "",
            "# Verify the restored known-good files, hashes, versions, vermagic, and loaded state.",
        ]
    )
    for name in loaded_modules:
        lines.extend(shell_test_module(name, records[name]))
    lines.append(
        f"test \"$(cat /sys/module/nvidia/version)\" = {shlex.quote(expected)}"
    )
    for parameter in ("modeset", "fbdev"):
        value = parameters.get(parameter)
        if value is not None:
            lines.append(
                f"test \"$(cat /sys/module/nvidia_drm/parameters/{parameter})\" = {shlex.quote(str(value))}"
            )
    lines.extend(
        [
            "sudo systemctl isolate graphical.target",
            "```",
            "",
            "If an unload, load, path, hash, version, vermagic, parameter, or graphical-target check fails, remain in text mode and use the independently tested known-good boot entry. Do not force a module operation and do not continue the experiment.",
            "",
            "## Pre-execution manual checks",
            "",
            "- [ ] This plan and its source snapshot are stored offline on a second device.",
            "- [ ] SSH and local TTY access were tested in the current boot.",
            "- [ ] The known-good boot entry was tested.",
            "- [ ] The module paths and hashes above still match the filesystem.",
            "- [ ] Explicit approval covers unload, local `insmod`, restoration, and any separate reboot.",
            "",
        ]
    )
    return "\n".join(lines)


def self_test() -> None:
    snapshot = {
        "schema_version": 1,
        "kernel_release": "6.8.0-test",
        "expected_version": "610.57.04",
        "nvidia_drm_parameters": {"modeset": "Y", "fbdev": "N"},
        "modules": [
            {"name": "nvidia", "filename": "/lib/nvidia.ko", "sha256": "a" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "loaded": True},
            {"name": "nvidia_modeset", "filename": "/lib/nvidia-modeset.ko", "sha256": "b" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "loaded": True},
            {"name": "nvidia_drm", "filename": "/lib/nvidia-drm.ko", "sha256": "c" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "loaded": True},
            {"name": "nvidia_uvm", "filename": "/lib/nvidia-uvm.ko", "sha256": "d" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "loaded": True},
        ],
    }
    text = render(snapshot)
    assert "unload_nvidia_stack" in text
    assert "sudo modprobe nvidia_uvm" in text
    assert "sha256sum" in text
    assert "/parameters/modeset" in text
    assert validate_snapshot(snapshot) == []
    broken = json.loads(json.dumps(snapshot))
    broken["modules"][0]["loaded"] = False
    assert validate_snapshot(broken)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "snapshot.json"
        path.write_text(json.dumps(snapshot))
        assert validate_snapshot(json.loads(path.read_text())) == []
    print("render-exp0006-rollback self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.snapshot is None:
        parser.error("snapshot is required unless --self-test is used")
    snapshot = json.loads(args.snapshot.read_text())
    output = render(snapshot)
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite {args.output}")
        args.output.write_text(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
