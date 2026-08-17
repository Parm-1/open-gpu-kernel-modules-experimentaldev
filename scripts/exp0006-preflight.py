#!/usr/bin/env python3
"""Read-only preflight for EXP-0006.

The tool collects only the minimum host facts needed for an exact-kernel build
and human recovery review. Its command runner accepts a small allowlist of
read-only commands and rejects module, privilege, service-state, and reboot
operations before execution.
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
EXPECTED_GPU_SUBSTRING = "RTX 2060"
REQUIRED_MODULES = ("nvidia", "nvidia_modeset", "nvidia_drm")
OPTIONAL_MODULES = ("nvidia_uvm", "nvidia_peermem")
STATUS_ORDER = {"PASS": 0, "WARN": 1, "BLOCK": 2}
MODINFO_FIELDS = {"version", "vermagic", "signer"}


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


def validate_read_only_command(argv: Sequence[str]) -> None:
    """Reject anything outside the preflight's explicit read-only command set."""
    args = list(argv)
    if not args:
        raise ValueError("empty command")
    executable = Path(args[0]).name
    tail = args[1:]

    allowed = False
    if executable == "git":
        allowed = tail in (["rev-parse", "HEAD"], ["status", "--porcelain"])
    elif executable == "modinfo":
        allowed = (
            len(tail) == 2
            and tail[0] == "-n"
            and tail[1] in REQUIRED_MODULES + OPTIONAL_MODULES
        ) or (
            len(tail) == 3
            and tail[0] == "-F"
            and tail[1] in MODINFO_FIELDS
            and tail[2] in REQUIRED_MODULES + OPTIONAL_MODULES
        )
    elif executable == "nvidia-smi":
        allowed = tail == [
            "--query-gpu=driver_version,name",
            "--format=csv,noheader,nounits",
        ]
    elif executable == "mokutil":
        allowed = tail == ["--sb-state"]
    elif executable == "systemctl":
        allowed = tail in (["is-active", "ssh"], ["is-active", "sshd"])

    if not allowed:
        raise ValueError(f"command is outside the read-only allowlist: {args!r}")


def run_command(
    name: str,
    argv: Sequence[str],
    timeout: int = 20,
    cwd: Path | None = None,
) -> CommandResult:
    validate_read_only_command(argv)
    try:
        proc = subprocess.run(
            list(argv),
            cwd=cwd,
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


def vermagic_matches(vermagic: str | None, kernel_release: str) -> bool:
    return bool(vermagic and vermagic.split(maxsplit=1)[0] == kernel_release)


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
        {
            "platform": sys.platform,
            "machine": machine,
            "kernel_release": kernel_release,
            "wsl_detected": wsl,
        },
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

    git_head = run_command("git-head", ["git", "rev-parse", "HEAD"], cwd=repo_root)
    git_status = run_command("git-status", ["git", "status", "--porcelain"], cwd=repo_root)
    commit = git_head.stdout.strip() if git_head.returncode == 0 else None
    dirty = bool(git_status.stdout.strip()) if git_status.returncode == 0 else None

    problems: list[str] = []
    if missing:
        problems.append("missing source symbols")
    if not commit:
        problems.append("source tree is not a readable Git checkout")
    if dirty is None:
        problems.append("source cleanliness could not be determined")
    elif dirty:
        problems.append("source tree has uncommitted or untracked changes")

    ok = not problems
    return (
        Check(
            "source-tree",
            "PASS" if ok else "BLOCK",
            "Merged read-only implementation is present in a clean Git checkout." if ok else "Source identity is ambiguous.",
            {"commit": commit, "dirty": dirty, "missing_symbols": missing, "problems": problems},
            None if ok else "Use a clean checkout of main at or after merge e9507b77cd2075c82ad34353660666ae58ccf502.",
        ),
        [git_head, git_status],
    )


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
    required = (
        "git",
        "make",
        "cc",
        "modinfo",
        "nvidia-smi",
        "sha256sum",
        "python3",
        "drm_info",
        "modetest",
        "nvidia-bug-report.sh",
    )
    optional = ("mokutil", "systemctl")
    required_paths = {name: shutil.which(name) for name in required}
    optional_paths = {name: shutil.which(name) for name in optional}
    missing = [name for name, value in required_paths.items() if value is None]
    if missing:
        return Check(
            "tools",
            "BLOCK",
            "Required build or evidence tools are missing.",
            {"required": required_paths, "optional": optional_paths},
            "Install: " + ", ".join(missing),
        )
    if any(value is None for value in optional_paths.values()):
        return Check(
            "tools",
            "WARN",
            "Core tools are present; Secure Boot or service checks need manual verification.",
            {"required": required_paths, "optional": optional_paths},
            "Install mokutil/systemd tooling or document equivalent checks before approval.",
        )
    return Check(
        "tools",
        "PASS",
        "Required build and evidence tools are available.",
        {"required": required_paths, "optional": optional_paths},
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
    exists = bool(path and path.is_file())
    digest: str | None = None
    hash_error: str | None = None
    if exists and path is not None:
        try:
            digest = sha256_file(path)
        except OSError as exc:
            hash_error = str(exc)
    return {
        "name": module,
        "filename": filename,
        "exists": exists,
        "sha256": digest,
        "hash_error": hash_error,
        "version": results[1].stdout.strip() if results[1].returncode == 0 else None,
        "vermagic": results[2].stdout.strip() if results[2].returncode == 0 else None,
        "signer": results[3].stdout.strip() if results[3].returncode == 0 else None,
    }, results


def check_driver_stack(
    expected_version: str,
    expected_gpu_substring: str,
    kernel_release: str,
) -> tuple[Check, dict[str, Any], list[CommandResult]]:
    module_records: list[dict[str, Any]] = []
    commands: list[CommandResult] = []
    for module in REQUIRED_MODULES + OPTIONAL_MODULES:
        record, results = module_metadata(module)
        module_records.append(record)
        commands.extend(results)

    proc_modules = text_or_none(Path("/proc/modules")) or ""
    loaded = {line.split()[0] for line in proc_modules.splitlines() if line.strip()}
    for record in module_records:
        record["loaded"] = record["name"] in loaded

    smi = run_command(
        "nvidia-smi-driver",
        ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader,nounits"],
    )
    commands.append(smi)
    userspace_version, gpu_names = parse_nvidia_smi_driver(smi.stdout) if smi.returncode == 0 else (None, [])
    modeset = text_or_none(Path("/sys/module/nvidia_drm/parameters/modeset"))
    fbdev = text_or_none(Path("/sys/module/nvidia_drm/parameters/fbdev"))

    problems: list[str] = []
    for record in module_records:
        name = str(record["name"])
        required = name in REQUIRED_MODULES
        relevant = required or bool(record["loaded"])
        if required and not record["exists"]:
            problems.append(f"missing installed module: {name}")
        if required and not record["sha256"]:
            problems.append(f"module hash unavailable: {name}")
        if relevant and record["version"] != expected_version:
            problems.append(f"{name} version is {record['version'] or 'unknown'}, expected {expected_version}")
        if relevant and not vermagic_matches(record["vermagic"], kernel_release):
            problems.append(f"{name} vermagic does not match {kernel_release}")
        if required and not record["loaded"]:
            problems.append(f"required module is not loaded: {name}")

    if userspace_version != expected_version:
        problems.append(f"userspace driver is {userspace_version or 'unknown'}, expected {expected_version}")
    if len(gpu_names) != 1:
        problems.append(f"expected one NVIDIA GPU, found {len(gpu_names)}")
    elif expected_gpu_substring.lower() not in gpu_names[0].lower():
        problems.append(f"GPU {gpu_names[0]!r} does not match target {expected_gpu_substring!r}")
    if "nouveau" in loaded:
        problems.append("nouveau is loaded")
    if modeset not in {"Y", "1"}:
        problems.append(f"nvidia_drm modeset is {modeset or 'unknown'}, expected enabled")

    status = "PASS" if not problems else "BLOCK"
    snapshot = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "kernel_release": kernel_release,
        "expected_version": expected_version,
        "expected_gpu_substring": expected_gpu_substring,
        "gpu_names": gpu_names,
        "modules": module_records,
        "nvidia_drm_parameters": {"modeset": modeset, "fbdev": fbdev},
    }
    return (
        Check(
            "nvidia-stack",
            status,
            "Installed and loaded NVIDIA stack matches the pinned target." if status == "PASS" else "The NVIDIA stack does not match the pinned target.",
            {
                "expected_version": expected_version,
                "expected_gpu_substring": expected_gpu_substring,
                "userspace_version": userspace_version,
                "gpu_names": gpu_names,
                "nouveau_loaded": "nouveau" in loaded,
                "modeset": modeset,
                "problems": problems,
            },
            None if status == "PASS" else "Boot one coherent NVIDIA 610.57.04 RTX 2060 stack with nvidia-drm KMS enabled before building or loading the experiment.",
        ),
        snapshot,
        commands,
    )


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
        status, summary = "WARN", "Turing GSP firmware was found outside the pinned-release directory."
        resolution = "Confirm from the package manifest that the firmware belongs to NVIDIA 610.57.04."
    else:
        status, summary = "WARN", "Turing GSP firmware was not found in standard filesystem locations."
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
            "Record firmware Secure Boot state manually before approval.",
        )
    elif "enabled" in combined:
        check = Check(
            "secure-boot",
            "WARN",
            "Secure Boot is enabled; runtime requires a tested signing and enrollment path.",
            {"state": result.stdout.strip()},
            "Build signed modules only after the key, public certificate, enrollment state, and recovery path are reviewed. Do not attempt an unsigned load.",
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
    statuses: list[dict[str, Any]] = []
    for status_path in sorted(Path("/sys/class/drm").glob("card*-*/status")):
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
        ("manual-second-device-ssh", "SSH login from a second device has been tested in the current boot."),
        ("manual-local-tty", "Local TTY login has been tested."),
        ("manual-offline-rollback", "Rollback commands and the known-good snapshot are stored offline."),
        ("manual-gsp-identity", "The active GSP firmware package identity has been verified."),
        ("manual-display-mode", "The sole display is SDR 1920×1080 60 Hz with HDR and VRR disabled."),
        ("manual-approval", "Operation-scoped module and any separate reboot approval have been recorded."),
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
            "Passing this preflight proves only readiness for an exact-kernel build and human recovery review. It does not prove `CAPABILITY_ADVERTISED` or any later security state.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    output_dir: Path,
    report: dict[str, Any],
    snapshot: dict[str, Any],
    commands: list[CommandResult],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "preflight.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / "preflight.md").write_text(render_markdown(report))
    (output_dir / "known-good-modules.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    with (output_dir / "commands.jsonl").open("w") as stream:
        for result in commands:
            stream.write(json.dumps(command_record(result), sort_keys=True) + "\n")
    (output_dir / "README.txt").write_text(
        "Read-only EXP-0006 preflight artifacts. Review local filesystem paths and every file before sharing. No EDID bytes, host name, hardware serial, credentials, keys, certificates, licenses, or media were queried.\n"
    )
    hash_lines = [
        f"{sha256_file(path)}  {path.name}"
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "artifacts.sha256"
    ]
    (output_dir / "artifacts.sha256").write_text("\n".join(hash_lines) + "\n")


def self_test() -> None:
    assert connector_is_direct_dp("card0-DP-1")
    assert connector_is_direct_dp("card12-DP-4")
    assert not connector_is_direct_dp("card0-DP-1-1")
    assert not connector_is_direct_dp("card0-HDMI-A-1")
    version, names = parse_nvidia_smi_driver("610.57.04, NVIDIA GeForce RTX 2060\n")
    assert version == "610.57.04" and names == ["NVIDIA GeForce RTX 2060"]
    assert vermagic_matches("6.8.0-137-generic SMP preempt mod_unload", "6.8.0-137-generic")
    assert not vermagic_matches("6.8.0-136-generic SMP", "6.8.0-137-generic")
    validate_read_only_command(["git", "rev-parse", "HEAD"])
    validate_read_only_command(["modinfo", "-F", "version", "nvidia"])
    for forbidden in (
        ["modprobe", "-r", "nvidia"],
        ["sudo", "modprobe", "-r", "nvidia"],
        ["systemctl", "isolate", "multi-user.target"],
        ["sh", "-c", "true"],
    ):
        try:
            validate_read_only_command(forbidden)
        except ValueError:
            pass
        else:
            raise AssertionError(f"forbidden command accepted: {forbidden}")
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
    parser.add_argument("--expected-gpu-substring", default=EXPECTED_GPU_SUBSTRING)
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
    driver_check, snapshot, driver_commands = check_driver_stack(
        args.expected_driver_version,
        args.expected_gpu_substring,
        args.kernel_release,
    )
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
    overall = (
        "BLOCKED"
        if highest == STATUS_ORDER["BLOCK"]
        else "MANUAL_REVIEW_REQUIRED"
        if highest == STATUS_ORDER["WARN"]
        else "AUTOMATED_CHECKS_PASS"
    )
    report = {
        "schema_version": 1,
        "experiment": "EXP-0006-read-only-nvkms-hdcp",
        "generated_at": utc_now(),
        "overall": overall,
        "expected_driver_version": args.expected_driver_version,
        "expected_gpu_substring": args.expected_gpu_substring,
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
