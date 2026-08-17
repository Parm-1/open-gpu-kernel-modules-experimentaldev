#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

LINE_RE = re.compile(
    r"HDCP_PROBE\s+display=(0x[0-9a-fA-F]+)\s+transport=(\d+)\s+"
    r"query_result=(\d+)\s+rm_status=(0x[0-9a-fA-F]+)\s+"
    r"flags=(0x[0-9a-fA-F]+)\s+valid=(\d+)"
)

QUERY_RESULTS = {
    0: "SUCCESS",
    1: "INVALID_ARGUMENT",
    2: "UNSUPPORTED_ROUTE",
    3: "NO_DEVICE",
    4: "NOT_PLUGGED",
    5: "NO_MAIN_LINK",
    6: "RM_FAILURE",
}

# Bit positions from NV0073_CTRL_SPECIFIC_HDCP_STATE_* in the pinned 610.57.04
# ctrl0073specific.h. Do not infer additional fields from other releases.
FLAG_BITS = {
    "encrypting": 0,
    "hdcp22_encryption_in_progress": 2,
    "attach_point_capable": 4,
    "attach_point_disallowed": 6,
    "receiver_capable": 8,
    "repeater_capable": 9,
    "internal_panel": 10,
    "hdcp22_receiver_capable": 11,
    "hdcp22_repeater_capable": 12,
    "hdcp22_encrypting": 13,
    "hdcp22_type1": 14,
    "authenticated": 15,
    "attach_point_hdcp22_capable": 16,
}


def decode_line(line: str) -> dict[str, object] | None:
    match = LINE_RE.search(line)
    if not match:
        return None
    display, transport_s, query_s, rm_s, flags_s, valid_s = match.groups()
    transport = int(transport_s)
    query_result = int(query_s)
    flags = int(flags_s, 16)
    valid = int(valid_s)
    decoded = {name: bool(flags & (1 << bit)) for name, bit in FLAG_BITS.items()}

    if transport != 1:
        outcome = "TRANSPORT_FAILURE"
    elif query_result != 0:
        outcome = QUERY_RESULTS.get(query_result, f"UNKNOWN_QUERY_RESULT_{query_result}")
    elif valid != 1:
        outcome = "INVALID_SUCCESS_STATE"
    else:
        outcome = "VALID_STATE"

    consistency: list[str] = []
    if decoded["hdcp22_type1"] and not decoded["hdcp22_encrypting"]:
        consistency.append("TYPE1_WITHOUT_HDCP22_ENCRYPTING")
    if decoded["hdcp22_encrypting"] and not decoded["authenticated"]:
        consistency.append("HDCP22_ENCRYPTING_WITHOUT_AUTHENTICATED")
    if valid != 1 and flags != 0:
        consistency.append("FLAGS_PRESENT_WHILE_INVALID")

    return {
        "display": display.lower(),
        "transport": bool(transport),
        "query_result": query_result,
        "query_result_name": QUERY_RESULTS.get(query_result, "UNKNOWN"),
        "rm_status": rm_s.lower(),
        "flags": flags_s.lower(),
        "valid": bool(valid),
        "outcome": outcome,
        "decoded_flags": decoded,
        "consistency_warnings": consistency,
        "claim_boundary": (
            "Raw authoritative state observation only; Gate 1 requires topology "
            "controls and independent reproduction."
        ),
    }


def input_lines(paths: list[Path]) -> Iterable[str]:
    if not paths:
        yield from sys.stdin
        return
    for path in paths:
        with path.open(errors="replace") as stream:
            yield from stream


def self_test() -> None:
    flags = (1 << 11) | (1 << 16)
    sample = (
        "kernel: HDCP_PROBE display=0x00000100 transport=1 query_result=0 "
        f"rm_status=0x00000000 flags=0x{flags:08x} valid=1"
    )
    decoded = decode_line(sample)
    assert decoded is not None
    assert decoded["outcome"] == "VALID_STATE"
    assert decoded["decoded_flags"]["hdcp22_receiver_capable"] is True
    assert decoded["decoded_flags"]["attach_point_hdcp22_capable"] is True
    assert decoded["decoded_flags"]["authenticated"] is False
    assert decode_line("unrelated kernel line") is None
    print("decode-hdcp-probe self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decode experimental NVIDIA HDCP_PROBE kernel log lines."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    records = [record for line in input_lines(args.paths) if (record := decode_line(line))]
    if not records:
        print("no HDCP_PROBE records found", file=sys.stderr)
        return 1
    json.dump(records, sys.stdout, indent=None if args.compact else 2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
