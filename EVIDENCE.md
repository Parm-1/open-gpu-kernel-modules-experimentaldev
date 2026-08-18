# Evidence register

Labels: `PROVEN_SOURCE`, `PROVEN_BUILD`, `PROVEN_RUNTIME`, `INFERRED`, `UNKNOWN`.

| ID | Label | Claim | Source or experiment |
|---|---|---|---|
| EV-0001 | PROVEN_SOURCE | `590.48.01` returns hard-coded unsupported DP HDCP state | pinned source |
| EV-0002 | PROVEN_SOURCE | `595.44.02` queries RM for HDCP state | pinned source |
| EV-0003 | PROVEN_SOURCE | `610.57.04` contains DP HDCP query/control and Type 1 logic | pinned source |
| EV-0004 | PROVEN_SOURCE | DP group logic manages auth retries and stream encryption | `dp_groupimpl.cpp` |
| EV-0005 | PROVEN_SOURCE | Baseline NVKMS KAPI had no HDCP surface | baseline KAPI headers/source |
| EV-0006 | PROVEN_SOURCE | Baseline `nvidia-drm` attached no standard content-protection property | baseline connector source |
| EV-0007 | PROVEN_BUILD | DP/RM-owned raw state query compiles in the complete module set | commit `cd5f5634...` |
| EV-0008 | PROVEN_BUILD | Dedicated NVKMS ioctl/KAPI path compiles and preserves detailed errors | commit `6918273d...` |
| EV-0009 | PROVEN_BUILD | Default-off `nvidia-drm` structured diagnostic compiles | commit `eb6cb2f4...` |
| EV-0010 | PROVEN_BUILD | Experimental ioctl and KAPI additions are append-only and rebuild cleanly | commit `3759ee6d...` |
| EV-0011 | PROVEN_BUILD | Final implementation head passed all six checks, including complete module compilation | commit `de4bc76f...`, Actions run `32024540017` |
| EV-0012 | PROVEN_SOURCE | Read-only implementation is integrated into `main` | merge `e9507b77...` |
| EV-0013 | UNKNOWN | RTX 2060 Linux RM/GSP returns meaningful state | EXP-0006 pending |
| EV-0014 | UNKNOWN | Target route authenticates HDCP 2.2 Type 1 | later Gate 2 experiment |
| EV-0015 | UNKNOWN | NVIDIA Vulkan Linux advertises protected memory/video/presentation | EXP-0004 pending |
| EV-0016 | PROVEN_BUILD | Runtime-readiness tools compile and pass deterministic confinement, loaded-identity, rollback, and baseline-artifact tests | PR #3 implementation `94a50cc2...` |
| EV-0017 | PROVEN_BUILD | Runtime-readiness candidate completes a deterministic full NVIDIA module build, validates version/`vermagic`/`srcversion`, records text-only hashes, and cleans generated modules | PR #3 implementation `94a50cc2...` |
| EV-0018 | PROVEN_SOURCE | EXP-0006 is defined as one default-off negative control plus two identical enabled clean-boot replications with exact-build binding and verified restoration | `docs/runtime/EXP-0006-native-protocol.md` |
| EV-0019 | UNKNOWN | Native preflight and recovery requirements are satisfied on the target RTX 2060 machine | EXP-0006 Phase A–D pending |
| EV-0020 | UNKNOWN | Enabled HDCP state observations reproduce under the required controls | EXP-0006 Sessions 2–3 pending |
| EV-0021 | PROVEN_SOURCE | `mfcdm-probe` uses the public Media Foundation discovery path and stops at `IsTypeSupported` without CDM access/session/license/network/media operations | `probes/mfcdm/`, EXP-0007 |
| EV-0022 | PROVEN_BUILD | `mfcdm-probe.exe` builds with MSVC warnings as errors and passes deterministic self-test, prohibited-source, and direct-network-import checks | commit `f1960bfb...`, `mfcdm-probe` workflow |
| EV-0023 | UNKNOWN | Public Media Foundation CDM discovery reaches a particular stage on native Windows | EXP-0007 Windows run pending |
| EV-0024 | UNKNOWN | Public Media Foundation CDM discovery reaches the same or an earlier stage under Wine | EXP-0007 Wine run pending |
