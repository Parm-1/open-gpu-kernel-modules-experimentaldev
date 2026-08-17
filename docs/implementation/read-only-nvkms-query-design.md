# Read-only NVKMS HDCP query design

Status: design for EXP-0006; no runtime claim.

## Objective

Determine whether a normal Linux NVKMS client on the target GeForce RTX 2060 can obtain meaningful authoritative HDCP state from the existing DP/RM path.

## Deliberate exclusions

The first patch must not request authentication, select Type 0 or Type 1, attach `Content Protection` or `HDCP Content Type`, expose a writable userspace control, claim hardware protection, or support HDMI/MST/cloning/adapters.

## Proposed vertical slice

1. Add a dedicated read-only NVKMS query for one `NVDpyId`.
2. Resolve the corresponding direct-DP-SST group/main-link owner.
3. Invoke the existing authoritative state method.
4. Return a validity mask, raw result, and individual fields.
5. Add a temporary read-only DRM debugfs report or opt-in diagnostic log.
6. Record raw command status and state before/after a harmless topology change.

## Fail-closed result model

```text
query transport failure     → validMask = 0, exact raw status retained
unsupported route           → explicit UNSUPPORTED_ROUTE, no booleans inferred
disconnected display        → explicit DISCONNECTED
authoritative false value   → field valid + false
successful state query      → only returned fields are marked valid
```

## Candidate files

```text
src/nvidia-modeset/interface/nvkms-api.h
src/nvidia-modeset/src/nvkms-dpy.c
src/nvidia-modeset/kapi/interface/nvkms-kapi.h
kernel-open/common/inc/nvkms-kapi.h
src/nvidia-modeset/kapi/src/nvkms-kapi.c
kernel-open/nvidia-drm/nvidia-drm-connector.[ch]
```

The exact DP helper file is intentionally unresolved. Do not add the query until source review proves how `NVDpyEvo` maps to the relevant DP group/main-link.

## Review gates

- The query performs no mutation.
- Duplicate KAPI headers remain byte-identical.
- ABI additions are appended unless build rules require otherwise.
- Unsupported routes fail explicitly.
- No module is loaded in CI.
- Runtime verdict uses a Gate 1 classification from `CHARTER.md`.
