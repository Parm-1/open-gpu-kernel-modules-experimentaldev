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


def module_parameter_argument(value: object) -> str | None:
    if value in {"Y", "1", 1, True}:
        return "1"
    if value in {"N", "0", 0, False}:
        return "0"
    return None


def validate_module_record(
    name: str,
    record: dict[str, Any],
    expected_version: str,
    *,
    require_loaded: bool,
) -> list[str]:
    errors: list[str] = []
    if require_loaded and record.get("loaded") is not True:
        errors.append(f"{name}: was not loaded in the known-good snapshot")

    filename = record.get("filename")
    if not isinstance(filename, str) or not filename:
        errors.append(f"{name}: missing filename")
    elif not Path(filename).is_absolute():
        errors.append(f"{name}: filename is not absolute")

    for field in ("version", "vermagic"):
        if not record.get(field):
            errors.append(f"{name}: missing {field}")
    if not valid_sha256(record.get("sha256")):
        errors.append(f"{name}: invalid or missing sha256")
    if record.get("version") != expected_version:
        errors.append(f"{name}: version does not match expected_version")

    on_disk_srcversion = record.get("srcversion")
    loaded_srcversion = record.get("loaded_srcversion")
    if on_disk_srcversion and loaded_srcversion and on_disk_srcversion != loaded_srcversion:
        errors.append(f"{name}: loaded srcversion differs from on-disk srcversion")
    return errors


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = snapshot.get("expected_version")
    if not isinstance(expected, str) or not expected:
        errors.append("missing expected_version")
        expected = ""
    kernel_release = snapshot.get("kernel_release")
    if not isinstance(kernel_release, str) or not kernel_release:
        errors.append("missing kernel_release")

    parameters = snapshot.get("nvidia_drm_parameters")
    if not isinstance(parameters, dict):
        errors.append("missing nvidia_drm_parameters")
    else:
        if module_parameter_argument(parameters.get("modeset")) != "1":
            errors.append("nvidia_drm modeset was not enabled in the known-good snapshot")
        fbdev = parameters.get("fbdev")
        if fbdev is not None and module_parameter_argument(fbdev) is None:
            errors.append("nvidia_drm fbdev has an unsupported value")

    records = module_by_name(snapshot)
    for name in REQUIRED_MODULES:
        record = records.get(name)
        if record is None:
            errors.append(f"missing module record: {name}")
            continue
        errors.extend(
            validate_module_record(name, record, expected, require_loaded=True)
        )

    for name in OPTIONAL_MODULES:
        record = records.get(name)
        if not record or record.get("loaded") is not True:
            continue
        errors.extend(
            validate_module_record(name, record, expected, require_loaded=True)
        )
    return errors


def shell_verify_on_disk(name: str, record: dict[str, Any]) -> list[str]:
    quoted_name = shlex.quote(name)
    expected_path = shlex.quote(str(record["filename"]))
    expected_hash = shlex.quote(str(record["sha256"]))
    expected_version = shlex.quote(str(record["version"]))
    expected_vermagic = shlex.quote(str(record["vermagic"]))
    lines = [
        f"test -f {expected_path}",
        f"test \"$(modinfo -n {quoted_name})\" = {expected_path}",
        f"test \"$(sha256sum {expected_path} | awk '{{print $1}}')\" = {expected_hash}",
        f"test \"$(modinfo -F version {quoted_name})\" = {expected_version}",
        f"test \"$(modinfo -F vermagic {quoted_name})\" = {expected_vermagic}",
    ]
    if record.get("srcversion"):
        lines.append(
            f"test \"$(modinfo -F srcversion {quoted_name})\" = {shlex.quote(str(record['srcversion']))}"
        )
    return lines


def shell_test_loaded_module(name: str, record: dict[str, Any]) -> list[str]:
    quoted_name = shlex.quote(name)
    lines = [f"test -d /sys/module/{quoted_name}"]
    lines.extend(shell_verify_on_disk(name, record))
    if record.get("loaded_srcversion"):
        lines.append(
            f"test \"$(cat /sys/module/{quoted_name}/srcversion)\" = {shlex.quote(str(record['loaded_srcversion']))}"
        )
    return lines


def shell_modprobe_command(name: str, parameters: dict[str, Any]) -> str:
    argv = ["sudo", "modprobe", name]
    if name == "nvidia_drm":
        for parameter in ("modeset", "fbdev"):
            value = module_parameter_argument(parameters.get(parameter))
            if value is not None:
                argv.append(f"{parameter}={value}")
    return shlex.join(argv)


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
    parameters = snapshot["nvidia_drm_parameters"]

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
        "| Module | Loaded | Path | SHA-256 | Version | Vermagic | On-disk srcversion | Loaded srcversion |",
        "|---|---:|---|---|---|---|---|---|",
    ]
    for name in ALL_MODULES:
        record = records.get(name)
        if record is None:
            continue
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                name,
                "yes" if record.get("loaded") else "no",
                record.get("filename") or "unavailable",
                record.get("sha256") or "unavailable",
                record.get("version") or "unavailable",
                record.get("vermagic") or "unavailable",
                record.get("srcversion") or "unavailable",
                record.get("loaded_srcversion") or "unavailable",
            )
        )

    lines.extend(
        [
            "",
            "## Intended recovery sequence",
            "",
            "Run only from working SSH or local TTY. Verify the resolver and known-good files before stopping the graphical session. Never use force-removal.",
            "",
            "```bash",
            "set -euo pipefail",
            f"test \"$(uname -r)\" = {shlex.quote(kernel_release)}",
            "",
            "# Fail before changing state if modprobe no longer resolves to the approved known-good files.",
        ]
    )
    for name in loaded_modules:
        lines.extend(shell_verify_on_disk(name, records[name]))

    lines.extend(
        [
            "",
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
        lines.append(shell_modprobe_command(name, parameters))

    lines.extend(
        [
            "",
            "# Verify the restored known-good files, hashes, versions, vermagic, srcversion, parameters, and loaded state.",
        ]
    )
    for name in loaded_modules:
        lines.extend(shell_test_loaded_module(name, records[name]))
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
            "If a pre-check, unload, load, path, hash, version, vermagic, srcversion, parameter, or graphical-target check fails, remain in text mode and use the independently tested known-good boot entry. Do not force a module operation and do not continue the experiment.",
            "",
            "## Pre-execution manual checks",
            "",
            "- [ ] This plan and its source snapshot are stored offline on a second device.",
            "- [ ] SSH and local TTY access were tested in the current boot.",
            "- [ ] The known-good boot entry was tested.",
            "- [ ] The module paths and hashes above still match the filesystem.",
            "- [ ] Any unavailable srcversion comparison was resolved or documented.",
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
            {"name": "nvidia", "filename": "/lib/nvidia.ko", "sha256": "a" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "srcversion": "SRC1", "loaded_srcversion": "SRC1", "loaded": True},
            {"name": "nvidia_modeset", "filename": "/lib/nvidia-modeset.ko", "sha256": "b" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "srcversion": "SRC2", "loaded_srcversion": "SRC2", "loaded": True},
            {"name": "nvidia_drm", "filename": "/lib/nvidia-drm.ko", "sha256": "c" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "srcversion": "SRC3", "loaded_srcversion": "SRC3", "loaded": True},
            {"name": "nvidia_uvm", "filename": "/lib/nvidia-uvm.ko", "sha256": "d" * 64, "version": "610.57.04", "vermagic": "6.8.0-test SMP", "srcversion": "SRC4", "loaded_srcversion": "SRC4", "loaded": True},
        ],
    }
    text = render(snapshot)
    assert "unload_nvidia_stack" in text
    assert "sudo modprobe nvidia_uvm" in text
    assert "sudo modprobe nvidia_drm modeset=1 fbdev=0" in text
    assert text.index("modinfo -n nvidia") < text.index("systemctl isolate multi-user.target")
    assert "sha256sum /lib/nvidia.ko" in text
    assert "modinfo -F srcversion" in text
    assert "/parameters/modeset" in text
    assert validate_snapshot(snapshot) == []
    broken = json.loads(json.dumps(snapshot))
    broken["modules"][0]["loaded"] = False
    assert validate_snapshot(broken)
    broken_path = json.loads(json.dumps(snapshot))
    broken_path["modules"][0]["filename"] = "relative/nvidia.ko"
    assert validate_snapshot(broken_path)
    broken_srcversion = json.loads(json.dumps(snapshot))
    broken_srcversion["modules"][0]["loaded_srcversion"] = "OTHER"
    assert validate_snapshot(broken_srcversion)
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
