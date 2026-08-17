# NVIDIA/Linux Protected-Media Research Fork

This repository is a research fork of NVIDIA's open GPU kernel modules. Its first objective is **not** to claim Netflix 4K support. It is to determine, with reproducible evidence, whether NVIDIA's current Linux display stack can truthfully expose HDCP 2.2 Type 1 through the standard Linux DRM/KMS content-protection interface.

The primary hardware target is an NVIDIA GeForce RTX 2060 connected directly over DisplayPort to one HDCP 2.2/2.3-capable display. The source baseline is NVIDIA release `610.57.04` at commit `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`.

## Current phase

- reproduce the transition from stubbed HDCP code in `590.48.01` to RM-backed code in `595.44.02` and later;
- map the disconnected call graphs between `nvidia-drm`, NVKMS KAPI, NVKMS, the DisplayPort library, and RM/GSP;
- collect native Linux and same-hardware Windows baselines without logging secrets;
- query Vulkan protected-resource capabilities without inferring support from the GPU model;
- design a read-only NVKMS HDCP state query before attaching any KMS property.

See [CHARTER.md](CHARTER.md), [PROJECT_STATE.md](PROJECT_STATE.md), and [TASKS.md](TASKS.md).

## Security and legal boundary

This project does not extract keys, copy credentials, spoof robustness levels, force premium manifests, or bypass service authorization. `Content Protection = Enabled` must never be reported unless the authoritative lower layer confirms authentication and active encryption.

## Experimental module warning

Nothing in the foundation branch installs or loads a kernel module. Loading a modified graphics module, changing boot state, or rebooting requires a separate recovery checklist and explicit approval.
