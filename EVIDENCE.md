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
| EV-0011 | PROVEN_BUILD | Final PR head passed all six checks, including complete module compilation | commit `de4bc76f...`, Actions run `32024540017` |
| EV-0012 | PROVEN_SOURCE | Read-only implementation is integrated into `main` | merge `e9507b77...` |
| EV-0013 | UNKNOWN | RTX 2060 Linux RM/GSP returns meaningful state | EXP-0006 pending |
| EV-0014 | UNKNOWN | Target route authenticates HDCP 2.2 Type 1 | later Gate 2 experiment |
| EV-0015 | UNKNOWN | NVIDIA Vulkan Linux advertises protected memory/video/presentation | EXP-0004 pending |
