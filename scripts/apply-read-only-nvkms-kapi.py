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


# NVKMS private API: command and parameter structures.
api_path = "src/nvidia-modeset/interface/nvkms-api.h"
api = read(api_path)
if "NVKMS_IOCTL_QUERY_DPY_HDCP_STATE" not in api:
    api = replace_once(
        api,
        "    NVKMS_IOCTL_QUERY_DPY_DYNAMIC_DATA,\n",
        "    NVKMS_IOCTL_QUERY_DPY_DYNAMIC_DATA,\n"
        "    NVKMS_IOCTL_QUERY_DPY_HDCP_STATE,\n",
        api_path,
    )

    params_anchor = (
        "struct NvKmsQueryDpyDynamicDataParams {\n"
        "    struct NvKmsQueryDpyDynamicDataRequest request; /*! in */\n"
        "    struct NvKmsQueryDpyDynamicDataReply reply;     /*! out */\n"
        "};\n"
    )
    params_block = params_anchor + (
        "\n"
        "/* Read-only HDCP state query. Detailed failures are returned in the reply. */\n"
        "struct NvKmsQueryDpyHdcpStateRequest {\n"
        "    NvKmsDeviceHandle deviceHandle;\n"
        "    NvKmsDispHandle dispHandle;\n"
        "    NVDpyId dpyId;\n"
        "};\n"
        "\n"
        "struct NvKmsQueryDpyHdcpStateReply {\n"
        "    NvU32 queryResult;\n"
        "    NvU32 rmStatus;\n"
        "    NvU32 flags;\n"
        "    NvBool valid;\n"
        "};\n"
        "\n"
        "struct NvKmsQueryDpyHdcpStateParams {\n"
        "    struct NvKmsQueryDpyHdcpStateRequest request; /*! in */\n"
        "    struct NvKmsQueryDpyHdcpStateReply reply;     /*! out */\n"
        "};\n"
    )
    api = replace_once(api, params_anchor, params_block, api_path)
    write(api_path, api)

# Core NVKMS handler and dispatch entry.
nvkms_path = "src/nvidia-modeset/src/nvkms.c"
nvkms = read(nvkms_path)
if "static NvBool QueryDpyHdcpState(" not in nvkms:
    nvkms = replace_once(
        nvkms,
        '#include "dp/nvdp-connector.h"\n',
        '#include "dp/nvdp-connector.h"\n#include "dp/nvdp-device.h"\n',
        nvkms_path,
    )
    handler_anchor = (
        "/*!\n"
        " * Perform the ioctl operation requested by the client.\n"
    )
    handler = (
        "static NvBool QueryDpyHdcpState(\n"
        "    struct NvKmsPerOpen *pOpen,\n"
        "    void *pParamsVoid)\n"
        "{\n"
        "    struct NvKmsQueryDpyHdcpStateParams *pParams = pParamsVoid;\n"
        "    NVDpyEvoPtr pDpyEvo;\n"
        "    NvDPHDCPRawState rawState = {0};\n"
        "    NvDPHDCPQueryResult queryResult;\n"
        "\n"
        "    pDpyEvo = GetPerOpenDpy(pOpen,\n"
        "                                pParams->request.deviceHandle,\n"
        "                                pParams->request.dispHandle,\n"
        "                                pParams->request.dpyId);\n"
        "    if (pDpyEvo == NULL) {\n"
        "        return FALSE;\n"
        "    }\n"
        "\n"
        "    queryResult = nvDPQueryHDCPRawState(pDpyEvo, &rawState);\n"
        "    pParams->reply.queryResult = (NvU32)queryResult;\n"
        "    pParams->reply.rmStatus = rawState.rmStatus;\n"
        "    pParams->reply.flags = rawState.flags;\n"
        "    pParams->reply.valid = rawState.valid;\n"
        "\n"
        "    /* The ioctl transport succeeded even when the detailed query did not. */\n"
        "    return TRUE;\n"
        "}\n"
        "\n"
    )
    nvkms = replace_once(nvkms, handler_anchor, handler + handler_anchor, nvkms_path)
    nvkms = replace_once(
        nvkms,
        "        ENTRY(NVKMS_IOCTL_QUERY_DPY_DYNAMIC_DATA, QueryDpyDynamicData),\n",
        "        ENTRY(NVKMS_IOCTL_QUERY_DPY_DYNAMIC_DATA, QueryDpyDynamicData),\n"
        "        ENTRY(NVKMS_IOCTL_QUERY_DPY_HDCP_STATE, QueryDpyHdcpState),\n",
        nvkms_path,
    )
    write(nvkms_path, nvkms)

# Public kernel KAPI. Both checked-in copies must stay byte-identical.
kapi_paths = [
    "kernel-open/common/inc/nvkms-kapi.h",
    "src/nvidia-modeset/kapi/interface/nvkms-kapi.h",
]
for kapi_path in kapi_paths:
    kapi = read(kapi_path)
    if "struct NvKmsKapiHdcpState" not in kapi:
        struct_anchor = "struct NvKmsKapiCreateSurfaceParams {\n"
        struct_block = (
            "/* Detailed result values match NvDPHDCPQueryResult in the DP bridge. */\n"
            "struct NvKmsKapiHdcpState {\n"
            "    NvU32 queryResult;\n"
            "    NvU32 rmStatus;\n"
            "    NvU32 flags;\n"
            "    NvBool valid;\n"
            "};\n"
            "\n"
        )
        kapi = replace_once(kapi, struct_anchor, struct_block + struct_anchor, kapi_path)

        function_anchor = (
            "    NvBool (*getDynamicDisplayInfo)\n"
            "    (\n"
            "        struct NvKmsKapiDevice *device,\n"
            "        struct NvKmsKapiDynamicDisplayParams *params\n"
            "    );\n"
        )
        function_block = function_anchor + (
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
        kapi = replace_once(kapi, function_anchor, function_block, kapi_path)
        write(kapi_path, kapi)

# KAPI implementation.
kapi_c_path = "src/nvidia-modeset/kapi/src/nvkms-kapi.c"
kapi_c = read(kapi_c_path)
if "static NvBool QueryHdcpState(" not in kapi_c:
    function_anchor = "static void FreeMemory\n(\n"
    function = (
        "static NvBool QueryHdcpState(\n"
        "    struct NvKmsKapiDevice *device,\n"
        "    NvKmsKapiDisplay display,\n"
        "    struct NvKmsKapiHdcpState *state)\n"
        "{\n"
        "    struct NvKmsQueryDpyHdcpStateParams params = { };\n"
        "    NvBool status;\n"
        "\n"
        "    if ((device == NULL) || (state == NULL)) {\n"
        "        return NV_FALSE;\n"
        "    }\n"
        "\n"
        "    nvkms_memset(state, 0, sizeof(*state));\n"
        "    params.request.deviceHandle = device->hKmsDevice;\n"
        "    params.request.dispHandle = device->hKmsDisp;\n"
        "    params.request.dpyId = nvNvU32ToDpyId(display);\n"
        "\n"
        "    status = nvkms_ioctl_from_kapi(device->pKmsOpen,\n"
        "                                   NVKMS_IOCTL_QUERY_DPY_HDCP_STATE,\n"
        "                                   &params, sizeof(params));\n"
        "    if (!status) {\n"
        "        nvKmsKapiLogDeviceDebug(device,\n"
        "            \"Failed to transport read-only HDCP state query for display 0x%08x\",\n"
        "            display);\n"
        "        return NV_FALSE;\n"
        "    }\n"
        "\n"
        "    state->queryResult = params.reply.queryResult;\n"
        "    state->rmStatus = params.reply.rmStatus;\n"
        "    state->flags = params.reply.flags;\n"
        "    state->valid = params.reply.valid;\n"
        "\n"
        "    return NV_TRUE;\n"
        "}\n"
        "\n"
    )
    kapi_c = replace_once(kapi_c, function_anchor, function + function_anchor, kapi_c_path)
    kapi_c = replace_once(
        kapi_c,
        "    funcsTable->getStaticDisplayInfo   = GetStaticDisplayInfo;\n"
        "    funcsTable->getDynamicDisplayInfo  = GetDynamicDisplayInfo;\n",
        "    funcsTable->getStaticDisplayInfo   = GetStaticDisplayInfo;\n"
        "    funcsTable->getDynamicDisplayInfo  = GetDynamicDisplayInfo;\n"
        "    funcsTable->queryHdcpState          = QueryHdcpState;\n",
        kapi_c_path,
    )
    write(kapi_c_path, kapi_c)

left = read(kapi_paths[0])
right = read(kapi_paths[1])
if left != right:
    raise SystemExit("duplicate NVKMS KAPI headers diverged")

print("read-only NVKMS HDCP KAPI source transformation complete")
