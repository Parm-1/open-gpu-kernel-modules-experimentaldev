#!/usr/bin/env python3
"""Read-only preflight for EXP-0006.

This program collects only the minimum host facts needed to decide whether the
native NVIDIA HDCP state experiment is ready for an exact-kernel build and a
human recovery review. It never installs, unloads, loads, signs, or reboots.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

EXPECTED_DRIVER_VERSION = "610.57.04"
REQUIRED_MODULES = ("nvidia", "nvidia_modeset", "nvidia_drm")
OPTIONAL_MODULES = ("nvidia_uvm", "nvidia_peermem")
STATUS_ORDER = {"PASS": 0, "WARN": 1, "BLOCK": 2}


@dataclasses.dataclass(frozen=True)
class CommandResult:
    name: str
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclasses.dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    summary: str
    evidence: dict[str, Any]
    resolution: str | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(name: str, argv: Sequence[str], timeout: int = 20) -> CommandResult:
    try:
        proc = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
        return CommandResult(name, list(argv), proc.returncode, proc.stdout, proc.stderr)
    except FileNotFoundError as exc:
        return CommandResult(name, list(argv), 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(name, list(argv), 124, stdout, stderr + "\ncommand timed out")


def text_or_none(path: Path) -> str | None:
    try:
        return path.read_text(errors="replace").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def parse_nvidia_smi_driver(stdout: str) -> tuple[str | None, list[str]]:
    versions: list[str] = []
    names: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",", 1)]
        versions.append(fields[0])
        if len(fields) == 2:
            names.append(fields[1])
    unique = sorted(set(versions))
    return (unique[0] if len(unique) == 1 else None), names


def connector_is_direct_dp(name: str) -> bool:
    return re.fullmatch(r"card\d+-DP-\d+", name) is not None


def version_matches(actual: str | None, expected: str) -> bool:
    return actual is not None and actual.strip() == expected


def command_record(result: CommandResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "argv": result.argv,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def check_native_linux(kernel_release: str) -> Check:
    proc_version = (text_or_none(Path("/proc/version")) or "").lower()
    wsl = "microsoft" in proc_version or "wsl" in kernel_release.lower()
    machine = platform.machine()
    ok = sys.platform.startswith("linux") and machine in {"x86_64", "amd64"} and not wsl
    return Check(
        "native-linux",
        "PASS" if ok else "BLOCK",
        "Native x86-64 Linux detected." if ok else "The target is not native x86-64 Linux.",
        {"platform": sys.platform, "machine": machine, "kernel_release": kernel_release, "wsl_detected": wsl},
        None if ok else "Boot the physical RTX 2060 machine into native x86-64 Linux; WSL/WSLg is source-work only.",
    )


def check_source(repo_root: Path) -> tuple[Check, list[CommandResult]]:
    required_symbols = {
        "src/common/displayport/src/dp_evoadapter.cpp": "queryHDCPRawState",
        "src/nvidia-modeset/src/nvkms.c": "NVKMS_IOCTL_QUERY_DPY_HDCP_STATE",
        "kernel-open/common/inc/nvkms-kapi.h": "queryHdcpState",
        "kernel-open/nvidia-drm/nvidia-drm-connector.c": "HDCP_PROBE",
    }
    missing: list[str] = []
    for relative, symbol in required_symbols.items():
        content = text_or_none(repo_root / relative)
        if content is None or symbol not in content:
            missing.append(f"{relative}:{symbol}")

    git = run_command("git-head", ["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    commit = git.stdout.strip() if git.returncode == 0 else None
    evidence = {"repo_root": str(repo_root), "commit": commit, "missing_symbols": missing}
    check = Check(
        "source-tree",
        "PASS" if not missing else "BLOCK",
        "Merged read-only HDCP implementation is present." if not missing else "The source tree is missing required EXP-0006 symbols.",
        evidence,
        None if not missing else "Use main at or after merge commit e9507b77cd2075c82ad34353660666ae58ccf502.",
    )
    return check, [git]


def check_kernel_build_tree(kernel_release: str) -> Check:
    build_dir = Path("/lib/modules") / kernel_release / "build"
    ok = build_dir.is_dir() and (build_dir / "Makefile").is_file()
    return Check(
        "kernel-build-tree",
        "PASS" if ok else "BLOCK",
        "Exact target-kernel build tree is available." if ok else "Exact target-kernel headers/build tree are missing.",
        {"kernel_release": kernel_release, "build_dir": str(build_dir), "exists": build_dir.exists()},
        None if ok else f"Install headers for {kernel_release} so {build_dir} exists.",
    )


def check_tools() -> Check:
    required = ("make", "cc", "modinfo", "sha256sum", "python3")
    optional = ("drm_info", "modetest", "nvidia-bug-report.sh", "mokutil", "systemctl")
    required_paths = {name: shutil.which(name) for name in required}
    optional_paths = {name: shutil.which(name) for name in optional}
    missing_required = [name for name, value in required_paths.items() if value is None]
    missing_evidence = [name for name in ("drm_info", "modetest", "nvidia-bug-report.sh") if optional_paths[name] is None]
    if missing_required or missing_evidence:
        status = "BLOCK"
    elif optional_paths["mokutil"] is None or optional_paths["systemctl"] is None:
        status = "WARN"
    else:
        status = "PASS"
    summary = "Required build and evidence tools are available."
    resolution = None
    if missing_required or missing_evidence:
        summary = "Required tools are missing."
        resolution = "Install: " + ", ".join(missing_required + missing_evidence)
    elif status == "WARN":
        summary = "Core tools are present; Secure Boot or service checks require manual verification."
        resolution = "Install mokutil/systemd tooling or document equivalent checks before approval."
    return Check(
        "tools",
        status,
        summary,
        {"required": required_paths, "optional": optional_paths},
        resolution,
    )


def module_metadata(module: str) -> tuple[dict[str, Any], list[CommandResult]]:
    results = [
        run_command(f"{module}-filename", ["modinfo", "-n", module]),
        run_command(f"{module}-version", ["modinfo", "-F", "version", module]),
        run_command(f"{module}-vermagic", ["modinfo", "-F", "vermagic", module]),
        run_command(f"{module}-signer", ["modinfo", "-F", "signer", module]),
    ]
    filename = results[0].stdout.strip() if results[0].returncode == 0 else None
    path = Path(filename) if filename and filename != "(builtin)" else None
    return {
        "name": module,
        "filename": filename,
        "exists": bool(path and path.is_file()),
        "sha256": sha256_file(path) if path and path.is_file() else None,
        "version": results[1].stdout.strip() if results[1].returncode == 0 else None,
        "vermagic": results[2].stdout.strip() if results[2].returncode == 0 else None,
        "signer": results[3].stdout.strip() if results[3].returncode == 0 else None,
    }, results


def check_driver_stack(expected: str) -> tuple[Check, dict[str, Any], list[CommandResult]]:
    module_records: list[dict[str, Any]] = []
    commands: list[CommandResult] = []
    for module in REQUIRED_MODULES + OPTIONAL_MODULES:
        record, results = module_metadata(module)
        module_records.append(record)
        commands.extend(results)

    required_records = [record for record in module_records if record["name"] in REQUIRED_MODULES]
    missing = [record["name"] for record in required_records if not record["exists"]]
    versions = sorted({str(record["version"]) for record in required_records if record["version"]})

    proc_modules = text_or_none(Path("/proc/modules")) or ""
    loaded = sorted({line.split()[0] for line in proc_modules.splitlines() if line.strip()})
    nouveau_loaded = "nouveau" in loaded
    missing_loaded = [module for module in REQUIRED_MODULES if module not in loaded]

    smi = run_command(
        "nvidia-smi-driver",
        ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader,nounits"],
    )
    commands.append(smi)
    userspace_version, gpu_names = parse_nvidia_smi_driver(smi.stdout) if smi.returncode == 0 else (None, [])

    problems: list[str] = []
    if missing:
        problems.append("missing installed modules: " + ", ".join(missing))
    if versions != [expected]:
        problems.append(f"module versions are {versions or ['unknown']}, expected {expected}")
    if userspace_version != expected:
        problems.append(f"userspace driver is {userspace_version or 'unknown'}, expected {expected}")
    if nouveau_loaded:
        problems.append("nouveau is loaded")
    if missing_loaded:
        problems.append("required NVIDIA modules are not loaded: " + ", ".join(missing_loaded))

    status = "PASS" if not problems else "BLOCK"
    check = Check(
        "nvidia-stack",
        status,
        "Installed and loaded NVIDIA stack matches the pinned release." if status == "PASS" else "The installed/loaded NVIDIA stack does not match the pinned release.",
        {
            "expected_version": expected,
            "userspace_version": userspace_version,
            "gpu_names": gpu_names,
            "loaded_required": [module for module in REQUIRED_MODULES if module in loaded],
            "nouveau_loaded": nouveau_loaded,
            "problems": problems,
        },
        None if status == "PASS" else "Install and boot one coherent NVIDIA 610.57.04 userspace, kernel-module, and GSP firmware stack before building or loading the experiment.",
    )
    for record in module_records:
        record["loaded"] = record["name"] in loaded
    snapshot = {
        "expected_version": expected,
        "modules": module_records,
        "nvidia_drm_parameters": {
            "modeset": text_or_none(Path("/sys/module/nvidia_drm/parameters/modeset")),
            "fbdev": text_or_none(Path("/sys/module/nvidia_drm/parameters/fbdev")),
        },
    }
    return check, snapshot, commands


def check_gsp_firmware(expected: str) -> Check:
    candidates = sorted(
        {
            *Path("/lib/firmware/nvidia").glob(f"{expected}/gsp_tu10x.bin*"),
            *Path("/lib/firmware/nvidia").glob("gsp_tu10x.bin*"),
        }
    )
    exact = [path for path in candidates if expected in path.parts]
    if exact:
        status, summary, resolution = "PASS", "Pinned-release Turing GSP firmware was found.", None
    elif candidates:
        status, summary = "WARN", "Turing GSP firmware was found, but not under the pinned release directory."
        resolution = "Confirm from the distribution package manifest that the firmware belongs to NVIDIA 610.57.04."
    else:
        status, summary = "WARN", "Turing GSP firmware was not found in the standard filesystem locations."
        resolution = "Locate and record the exact 610.57.04 GSP firmware source before approval; packaging layouts vary."
    return Check(
        "gsp-firmware",
        status,
        summary,
        {"candidates": [str(path) for path in candidates], "exact_version_candidates": [str(path) for path in exact]},
        resolution,
    )


def check_secure_boot() -> tuple[Check, CommandResult]:
    result = run_command("secure-boot", ["mokutil", "--sb-state"])
    combined = (result.stdout + "\n" + result.stderr).lower()
    if result.returncode != 0:
        check = Check(
            "secure-boot",
            "WARN",
            "Secure Boot state could not be determined automatically.",
            {"returncode": result.returncode},
            "Record firmware Secure Boot state manually. Unsigned experimental modules must not be attempted when enforcement is active.",
        )
    elif "enabled" in combined:
        check = Check(
            "secure-boot",
            "BLOCK",
            "Secure Boot is enabled; an unsigned local build will not load.",
            {"state": result.stdout.strip()},
            "Prepare a tested module-signing/enrollment path or use an expendable test boot with Secure Boot disabled before requesting approval.",
        )
    else:
        check = Check("secure-boot", "PASS", "Secure Boot is not reported as enabled.", {"state": result.stdout.strip()})
    return check, result


def check_ssh() -> tuple[Check, list[CommandResult]]:
    results = [
        run_command("ssh-service", ["systemctl", "is-active", "ssh"]),
        run_command("sshd-service", ["systemctl", "is-active", "sshd"]),
    ]
    active = any(result.returncode == 0 and result.stdout.strip() == "active" for result in results)
    return (
        Check(
            "ssh-recovery",
            "PASS" if active else "BLOCK",
            "An SSH service is active." if active else "No active SSH service was confirmed.",
            {"active": active},
            None if active else "Enable SSH and prove login from a second device before module-load approval.",
        ),
        results,
    )


def check_topology() -> Check:
    drm_root = Path("/sys/class/drm")
    statuses: list[dict[str, Any]] = []
    for status_path in sorted(drm_root.glob("card*-*/status")):
        state = text_or_none(status_path) or "unreadable"
        connector = status_path.parent.name
        driver_path = status_path.parent / "device" / "driver"
        try:
            driver = driver_path.resolve().name if driver_path.exists() else None
        except OSError:
            driver = None
        statuses.append({"connector": connector, "status": state, "driver": driver})

    connected = [entry for entry in statuses if entry["status"] == "connected"]
    problems: list[str] = []
    if len(connected) != 1:
        problems.append(f"expected exactly one connected connector, found {len(connected)}")
    elif not connector_is_direct_dp(str(connected[0]["connector"])):
        problems.append(f"connected route {connected[0]['connector']} is not direct DisplayPort SST")
    if connected and connected[0].get("driver") not in {"nvidia", "nvidia-drm"}:
        problems.append(f"connected route is owned by {connected[0].get('driver') or 'unknown driver'}")

    status = "PASS" if not problems else "BLOCK"
    return Check(
        "display-topology",
        status,
        "One direct NVIDIA DisplayPort SST connector is active." if status == "PASS" else "Display topology does not match EXP-0006.",
        {"connectors": statuses, "problems": problems},
        None if status == "PASS" else "Use one direct DP cable and one display; remove MST, HDMI, eDP, adapters, docks, KVMs, receivers, capture devices, and secondary outputs.",
    )


def manual_checks() -> list[Check]:
    items = [
        ("manual-expendable-install", "The native Linux installation is expendable or independently recoverable."),
        ("manual-known-good-boot", "A known-good kernel/NVIDIA boot entry has been boot-tested."),
        ("manual-local-tty", "Local TTY login has been tested."),
        ("manual-offline-rollback", "Rollback commands and the known-good module snapshot are stored offline."),
        ("manual-display-mode", "The sole display is SDR 1920×1080 60 Hz with HDR and VRR disabled."),
        ("manual-approval", "Explicit approval to install/load/reboot has been recorded."),
    ]
    return [
        Check(check_id, "WARN", statement, {"automatic_verification": False}, "Operator must check and record this item before execution.")
        for check_id, statement in items
    ]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# EXP-0006 preflight report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Overall: **{report['overall']}**",
        "",
        "This report is read-only. It does not authorize or perform module installation, loading, unloading, signing, boot changes, or rebooting.",
        "",
        "## Checks",
        "",
        "| Check | Status | Summary |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(f"| `{check['check_id']}` | **{check['status']}** | {check['summary']} |")
    blockers = [check for check in report["checks"] if check["status"] == "BLOCK"]
    warnings = [check for check in report["checks"] if check["status"] == "WARN"]
    if blockers:
        lines.extend(["", "## Blockers", ""])
        for check in blockers:
            lines.append(f"- `{check['check_id']}`: {check.get('resolution') or check['summary']}")
    if warnings:
        lines.extend(["", "## Manual or warning items", ""])
        for check in warnings:
            lines.append(f"- `{check['check_id']}`: {check.get('resolution') or check['summary']}")
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "Passing this preflight proves only that the machine appears ready for an exact-kernel build and human recovery review. It does not prove `CAPABILITY_ADVERTISED` or any later security state.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(output_dir: Path, report: dict[str, Any], snapshot: dict[str, Any], commands: list[CommandResult]) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "preflight.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / "preflight.md").write_text(render_markdown(report))
    (output_dir / "known-good-modules.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    with (output_dir / "commands.jsonl").open("w") as stream:
        for result in commands:
            stream.write(json.dumps(command_record(result), sort_keys=True) + "\n")
    (output_dir / "README.txt").write_text(
        "Read-only EXP-0006 preflight artifacts. Review before sharing. No EDID bytes, host name, account data, keys, certificates, licenses, or media were collected.\n"
    )
    hash_lines: list[str] = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "artifacts.sha256":
            hash_lines.append(f"{sha256_file(path)}  {path.name}")
    (output_dir / "artifacts.sha256").write_text("\n".join(hash_lines) + "\n")


def self_test() -> None:
    assert connector_is_direct_dp("card0-DP-1")
    assert connector_is_direct_dp("card12-DP-4")
    assert not connector_is_direct_dp("card0-DP-1-1")
    assert not connector_is_direct_dp("card0-HDMI-A-1")
    version, names = parse_nvidia_smi_driver("610.57.04, NVIDIA GeForce RTX 2060\n")
    assert version == "610.57.04" and names == ["NVIDIA GeForce RTX 2060"]
    version, _ = parse_nvidia_smi_driver("610.57.04, A\n609.00, B\n")
    assert version is None
    assert version_matches("610.57.04", EXPECTED_DRIVER_VERSION)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sample"
        path.write_bytes(b"abc")
        assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    sample = {
        "generated_at": "2026-08-17T00:00:00+00:00",
        "overall": "BLOCKED",
        "checks": [dataclasses.asdict(Check("x", "BLOCK", "blocked", {}, "fix it"))],
    }
    rendered = render_markdown(sample)
    assert "EXP-0006 preflight report" in rendered and "fix it" in rendered
    print("exp0006-preflight self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--kernel-release", default=platform.release())
    parser.add_argument("--expected-driver-version", default=EXPECTED_DRIVER_VERSION)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    checks: list[Check] = []
    commands: list[CommandResult] = []
    checks.append(check_native_linux(args.kernel_release))
    source_check, source_commands = check_source(args.repo_root.resolve())
    checks.append(source_check)
    commands.extend(source_commands)
    checks.append(check_kernel_build_tree(args.kernel_release))
    checks.append(check_tools())
    driver_check, snapshot, driver_commands = check_driver_stack(args.expected_driver_version)
    checks.append(driver_check)
    commands.extend(driver_commands)
    checks.append(check_gsp_firmware(args.expected_driver_version))
    secure_boot_check, secure_boot_command = check_secure_boot()
    checks.append(secure_boot_check)
    commands.append(secure_boot_command)
    ssh_check, ssh_commands = check_ssh()
    checks.append(ssh_check)
    commands.extend(ssh_commands)
    checks.append(check_topology())
    checks.extend(manual_checks())

    highest = max((STATUS_ORDER[check.status] for check in checks), default=0)
    overall = "BLOCKED" if highest == STATUS_ORDER["BLOCK"] else "MANUAL_REVIEW_REQUIRED" if highest == STATUS_ORDER["WARN"] else "AUTOMATED_CHECKS_PASS"
    report = {
        "schema_version": 1,
        "experiment": "EXP-0006-read-only-nvkms-hdcp",
        "generated_at": utc_now(),
        "overall": overall,
        "expected_driver_version": args.expected_driver_version,
        "kernel_release": args.kernel_release,
        "checks": [dataclasses.asdict(check) for check in checks],
        "claim_boundary": "Read-only readiness evidence only; no runtime security state is proven.",
    }

    if args.output_dir:
        write_outputs(args.output_dir, report, snapshot, commands)
    if args.print_json or not args.output_dir:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if overall == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
