#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text)


def replace_once(text: str, old: str, new: str, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


# Backing storage for the opt-in diagnostic parameter.
os_c = "kernel-open/nvidia-drm/nvidia-drm-os-interface.c"
text = read(os_c)
if "nv_drm_hdcp_probe_module_param" not in text:
    text = replace_once(
        text,
        "bool nv_drm_vblank_module_param = false;\n"
        "bool nv_drm_color_pipeline_module_param = true;\n",
        "bool nv_drm_vblank_module_param = false;\n"
        "bool nv_drm_hdcp_probe_module_param = false;\n"
        "bool nv_drm_color_pipeline_module_param = true;\n",
        os_c,
    )
    write(os_c, text)

os_h = "kernel-open/nvidia-drm/nvidia-drm-os-interface.h"
text = read(os_h)
if "nv_drm_hdcp_probe_module_param" not in text:
    text = replace_once(
        text,
        "/* Set to true when the vblank support feature is enabled. */\n"
        "extern bool nv_drm_vblank_module_param;\n",
        "/* Set to true when the vblank support feature is enabled. */\n"
        "extern bool nv_drm_vblank_module_param;\n"
        "/* Experimental read-only HDCP state report on connector detection. */\n"
        "extern bool nv_drm_hdcp_probe_module_param;\n",
        os_h,
    )
    write(os_h, text)

linux_c = "kernel-open/nvidia-drm/nvidia-drm-linux.c"
text = read(linux_c)
if "module_param_named(hdcp_probe" not in text:
    anchor = (
        "MODULE_PARM_DESC(\n"
        "    vblank,\n"
        "    \"Enable drm vblank notification support (1 = enable, 0 = disable (default))\");\n"
        "module_param_named(vblank, nv_drm_vblank_module_param, bool, 0400);\n"
    )
    block = anchor + (
        "\n"
        "MODULE_PARM_DESC(\n"
        "    hdcp_probe,\n"
        "    \"Log an experimental read-only HDCP state report during connector detection\");\n"
        "module_param_named(hdcp_probe, nv_drm_hdcp_probe_module_param, bool, 0400);\n"
    )
    text = replace_once(text, anchor, block, linux_c)
    write(linux_c, text)

connector_c = "kernel-open/nvidia-drm/nvidia-drm-connector.c"
text = read(connector_c)
if "nv_drm_report_hdcp_probe" not in text:
    helper_anchor = "static bool\n__nv_drm_detect_encoder("
    helper = (
        "static void nv_drm_report_hdcp_probe(\n"
        "    struct nv_drm_device *nv_dev,\n"
        "    NvKmsKapiDisplay display)\n"
        "{\n"
        "    struct NvKmsKapiHdcpState state = {0};\n"
        "    NvBool transport = NV_FALSE;\n"
        "\n"
        "    if (nvKms->queryHdcpState != NULL) {\n"
        "        transport = nvKms->queryHdcpState(\n"
        "            nv_dev->pDevice, display, &state);\n"
        "    }\n"
        "\n"
        "    NV_DRM_DEV_LOG_INFO(\n"
        "        nv_dev,\n"
        "        \"HDCP_PROBE display=0x%08x transport=%u query_result=%u rm_status=0x%08x flags=0x%08x valid=%u\",\n"
        "        display, transport ? 1U : 0U, state.queryResult,\n"
        "        state.rmStatus, state.flags, state.valid ? 1U : 0U);\n"
        "}\n"
        "\n"
    )
    text = replace_once(text, helper_anchor, helper + helper_anchor, connector_c)

    call_anchor = (
        "    if (!nvKms->getDynamicDisplayInfo(nv_dev->pDevice, pDetectParams)) {\n"
        "        NV_DRM_DEV_LOG_ERR(\n"
        "            nv_dev,\n"
        "            \"Failed to detect display state\");\n"
        "        return false;\n"
        "    }\n"
        "\n"
    )
    call_block = call_anchor + (
        "    if (nv_drm_hdcp_probe_module_param && pDetectParams->connected) {\n"
        "        nv_drm_report_hdcp_probe(nv_dev, pDetectParams->handle);\n"
        "    }\n"
        "\n"
    )
    text = replace_once(text, call_anchor, call_block, connector_c)
    write(connector_c, text)

if "queryHdcpState" not in read("kernel-open/common/inc/nvkms-kapi.h"):
    raise SystemExit("read-only NVKMS KAPI layer is not present")

print("read-only nvidia-drm HDCP diagnostic transformation complete")
