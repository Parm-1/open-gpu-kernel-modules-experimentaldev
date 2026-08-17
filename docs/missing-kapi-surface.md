# Missing NVKMS KAPI surface

Status: `PROVEN_SOURCE` for absence; proposed interface is `INFERRED`.

## What exists

`NvKmsKapiFunctionsTable` exposes display enumeration, connector/display information, modesets, surfaces, memory, synchronization, and events. `NvKmsKapiDynamicDisplayParams` returns connection, EDID, size, and VRR. No dedicated HDCP query/request/status/event operation is present.

`nvidia-drm-connector.c` does not attach `drm_connector_attach_content_protection_property()`.

## Minimum read-only shape

```c
struct NvKmsKapiHdcpState {
    NvU32 validMask;
    NvU32 rawStatus;
    NvBool hdcp1xCapable;
    NvBool hdcp22Capable;
    NvBool repeaterCapable;
    NvBool authenticated;
    NvBool encrypting;
    NvBool type1Active;
};

NvBool (*queryHdcpState)(
    struct NvKmsKapiDevice *device,
    NvKmsKapiDisplay display,
    struct NvKmsKapiHdcpState *state);
```

Names and layout remain provisional. Requirements:

- distinguish unsupported, unknown, command failure, and a real false value;
- expose raw lower-layer status;
- perform no authentication, stream-type, ECF, or modeset mutation;
- support only direct DP SST at first and reject other routes explicitly;
- never translate an error into authenticated or encrypting.

## Preferred plumbing

```text
nvidia-drm diagnostic
  → NVKMS KAPI queryHdcpState
    → dedicated NVKMS query ioctl/helper
      → NVDpy/DP library owner
        → existing authoritative HDCP state method
```

A dedicated query is preferred over silently expanding ordinary dynamic-display queries because it keeps security-state semantics explicit.
