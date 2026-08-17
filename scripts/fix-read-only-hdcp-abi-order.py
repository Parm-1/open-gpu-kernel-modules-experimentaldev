#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text)


api_path = "src/nvidia-modeset/interface/nvkms-api.h"
api = read(api_path)
command = "    NVKMS_IOCTL_QUERY_DPY_HDCP_STATE,\n"
if api.count(command) != 1:
    raise SystemExit(f"{api_path}: expected exactly one HDCP query command")
api = api.replace(command, "")
end_command = "    NVKMS_IOCTL_UNREGISTER_VBLANK_INTR_CALLBACK,\n};\n"
if api.count(end_command) != 1:
    raise SystemExit(f"{api_path}: ioctl enum end anchor changed")
api = api.replace(
    end_command,
    "    NVKMS_IOCTL_UNREGISTER_VBLANK_INTR_CALLBACK,\n"
    "    NVKMS_IOCTL_QUERY_DPY_HDCP_STATE,\n"
    "};\n",
    1,
)
write(api_path, api)

query_function = (
    "\n"
    "    /*!\n"
    "     * Query raw HDCP state without changing authentication or stream type.\n"
    "     * Detailed unsupported and RM failure states are returned in state.\n"
    "     */\n"
    "    NvBool (*queryHdcpState)\n"
    "    (\n"
    "        struct NvKmsKapiDevice *device,\n"
    "        NvKmsKapiDisplay display,\n"
    "        struct NvKmsKapiHdcpState *state\n"
    "    );\n"
)

table_end = "\n};\n\n/** @} */\n\n/**\n * \\defgroup Functions\n"
kapi_paths = [
    "kernel-open/common/inc/nvkms-kapi.h",
    "src/nvidia-modeset/kapi/interface/nvkms-kapi.h",
]
for path in kapi_paths:
    text = read(path)
    if text.count(query_function) != 1:
        raise SystemExit(f"{path}: expected exactly one queryHdcpState function block")
    text = text.replace(query_function, "", 1)
    position = text.rfind(table_end)
    if position < 0:
        raise SystemExit(f"{path}: function-table end anchor changed")
    text = text[:position] + query_function + text[position:]
    write(path, text)

if read(kapi_paths[0]) != read(kapi_paths[1]):
    raise SystemExit("duplicate NVKMS KAPI headers diverged")

print("HDCP experimental ABI additions moved to append-only positions")
