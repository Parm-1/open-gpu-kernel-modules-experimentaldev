# NVIDIA HDCP call-graph map

Status: mixed `PROVEN_SOURCE` and `INFERRED`.

## Existing Linux DRM/KMS display-query path

```text
kernel-open/nvidia-drm/nvidia-drm-connector.c
  __nv_drm_detect_encoder()
    nvKms->getDynamicDisplayInfo()
      src/nvidia-modeset/kapi/src/nvkms-kapi.c
        GetDynamicDisplayInfo()
          NVKMS_IOCTL_QUERY_DPY_DYNAMIC_DATA
            src/nvidia-modeset/src/nvkms-dpy.c
              nvDpyGetDynamicData()
```

That path returns connection, EDID, dimensions, VRR, and related display data. It does not return HDCP capability or state.

## Existing DisplayPort HDCP ownership path

```text
src/common/displayport/src/dp_groupimpl.cpp
  GroupImpl::hdcpSetEncrypted()
  GroupImpl::expired()
    DisplayPort::MainLink HDCP methods
      src/common/displayport/src/dp_evoadapter.cpp
        EvoMainLink::configureHDCPGetHDCPState()
        EvoMainLink::configureHDCPRenegotiate()
        EvoMainLink::configureHDCPDisableAuthentication()
        EvoMainLink::configureHDCPAbortAuthentication()
        EvoMainLink::configureHDCPValidateLink()
        EvoMainLink::setStreamType()
          EvoInterface::rmControl0073()
            RM/GSP/display hardware
```

## Current discontinuity

```text
nvidia-drm connector state
        X no public HDCP KAPI/IOCTL
NVKMS display / DP library owner
        ↓
RM-backed HDCP implementation
```

The first task is to bridge that discontinuity read-only while preserving the current ownership model. Direct RM controls from `nvidia-drm` would duplicate or bypass DP-library state and are rejected unless further source evidence proves they are intended.

## Open ownership questions

- Which NVKMS object safely identifies the `DisplayPort::Group` or main link for one `NVDpyId`?
- Is authoritative Type 1 state stored per link, group, or stream?
- Can SST state be queried without mutating auth timers or ECF state?
- What is the corresponding HDMI owner?
- Which event source should drive `Enabled → Desired` later?
