# Experiment registry

Every experiment directory contains a manifest, exact commands, raw stdout and stderr, artifact hashes, and a verdict. Raw files are never overwritten after collection. `NOT_RUN` placeholders are intentional and prevent planned work from being mistaken for evidence.

Current sequence:

1. EXP-0001 — reproduce NVIDIA source transition
2. EXP-0002 — inventory current KAPI/KMS exposure
3. EXP-0003 — collect native NVIDIA connector/property baseline
4. EXP-0004 — inventory Vulkan protected-resource capabilities
5. EXP-0005 — collect same-hardware Windows reference
6. EXP-0006 — query authoritative HDCP state through NVKMS
