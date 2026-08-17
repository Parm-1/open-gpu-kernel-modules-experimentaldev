# Evidence register

Labels: `PROVEN_SOURCE`, `PROVEN_RUNTIME`, `INFERRED`, `UNKNOWN`.

| ID | Label | Claim | Source or experiment |
|---|---|---|---|
| EV-0001 | PROVEN_SOURCE | `590.48.01` returns hard-coded unsupported DP HDCP state | commit `2ccbad...`, `dp_evoadapter.cpp`, `configureHDCPGetHDCPState` |
| EV-0002 | PROVEN_SOURCE | `595.44.02` queries RM for HDCP state | commit `2c7bfb...`, same symbol |
| EV-0003 | PROVEN_SOURCE | `610.57.04` can query, renegotiate, disable, abort, validate, and set stream type in the DP path | commit `e4a5faa...`, `dp_evoadapter.cpp` |
| EV-0004 | PROVEN_SOURCE | DP group logic manages auth retries, Type 0/1 selection, and stream encryption | commit `e4a5faa...`, `dp_groupimpl.cpp` |
| EV-0005 | PROVEN_SOURCE | NVKMS KAPI has no dedicated HDCP surface | both `nvkms-kapi.h` copies and `nvkms-kapi.c` |
| EV-0006 | PROVEN_SOURCE | `nvidia-drm` does not attach standard content-protection properties | `nvidia-drm-connector.c` |
| EV-0007 | INFERRED | A truthful bridge should preserve NVKMS/DP-library ownership rather than issue ad-hoc RM controls from `nvidia-drm` | EV-0003 through EV-0006 |
| EV-0008 | UNKNOWN | RTX 2060 Linux RM/GSP accepts meaningful HDCP state queries | EXP-0006 pending |
| EV-0009 | UNKNOWN | Target route authenticates HDCP 2.2 Type 1 | EXP-0003 pending |
| EV-0010 | UNKNOWN | NVIDIA Vulkan Linux advertises protected memory/video/presentation | EXP-0004 pending |
