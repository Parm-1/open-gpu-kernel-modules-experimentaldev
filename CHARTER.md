# Linux protected-media research charter

## Mission

Determine whether a legitimate, end-to-end hardware-protected media path can be built on native x86-64 Linux for an NVIDIA GeForce RTX 2060, implement reusable open-source components where technically possible, and identify exact vendor-controlled boundaries where it is not. Netflix 4K is the final service-level acceptance test, not the first task.

The desired chain is:

```text
approved hardware-secure CDM and device identity
  → secure license handling
  → protected compressed samples
  → protected decode and GPU memory
  → trusted protected presentation
  → Linux DRM/KMS HDCP 2.2 Type 1
  → direct RTX 2060 display route
  → service grants and sustains a 4K representation
```

Every layer must be proven independently.

## First research question

Can a community-built NVKMS/KMS bridge obtain authoritative HDCP capability and state, and then legitimately request HDCP 2.2 Type 1, using NVIDIA's current public source and shipped RM/GSP path?

The first driver experiment is read-only. It must not request authentication, select Type 1, or attach standard KMS content-protection properties.

## Required state vocabulary

Use the definitions in `docs/security-state-model.md`. Never conflate source presence, advertised capability, accepted request, authentication, encryption, Type 1, protected memory, protected decode, protected presentation, hardware protection, vendor attestation, service authorization, and end-to-end proof.

## Source baselines

- NVIDIA pre-change control: `590.48.01`, commit `2ccbad25e1af6a6ee6f38cf569f89f8b65d658ab`
- First known non-stub NVIDIA source: `595.44.02`, commit `2c7bfb47060233bda7c37c8065c0ddcac0d3da05`
- Primary NVIDIA baseline: `610.57.04`, commit `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Chromium reference seed: `8086bb60f151aad53b2a76fbaeeebf6855ea2c4c`
- Wine reference seed: `e99fc2f7587db7bc186293e9949fe0d3695cd430`

Do not silently move a baseline.

## Workstreams

1. **Source archaeology:** reproduce the NVIDIA transition, map ownership, and identify the missing KAPI rather than assuming it.
2. **NVIDIA KMS HDCP:** read-only state, authentication control, standard KMS properties, lifecycle correctness, and negative controls—in that order.
3. **Native protected resources:** query Vulkan protected memory, queues, WSI, and per-codec video support on the exact target stack.
4. **Windows reference:** same hardware, public diagnostics only, no secrets.
5. **Wine:** trace the exact Media Foundation/PMP/D3D11 first failure and implement only invoked interfaces with honest security states.
6. **Compositor/browser:** direct KMS, then Weston, then protocol and desktop integration; do not start with KDE/GNOME.
7. **Vendor authorization:** prepare precise technical packets only after lower layers produce evidence and only with explicit publication approval.
8. **Nova:** maintain a forward-port semantic map, but do not block the first proof on the shipping NVIDIA stack.

## Evidence gates

- **Gate 0:** exact source, hardware, firmware, connector ownership, KMS properties, Vulkan inventory, and Windows reference.
- **Gate 1:** truthful read-only NVIDIA HDCP state. Verdict must be one of `COMMUNITY_PATH_CONFIRMED`, `NARROW_NVIDIA_HOOK_REQUIRED`, `VENDOR_BACKEND_BLOCKED`, or `INCONCLUSIVE`.
- **Gate 2:** real, distinguishable Type 0/Type 1 authentication with negative-route and link-loss tests.
- **Gate 3:** standard KMS `Desired → Enabled → Desired` behavior and tests.
- **Gate 4+:** protected memory/decode/presentation, controlled compositor, legitimate DRM test material, vendor attestation, and finally service authorization.

No gate may be skipped by returning fake success.

## Initial physical topology

Use native Linux and:

```text
RTX 2060 → direct DisplayPort cable → one HDCP 2.2/2.3-capable display
```

Start at SDR 1920×1080 60 Hz. Remove secondary outputs, MST, docks, adapters, KVMs, receivers, capture devices, HDR, and VRR. WSL/WSLg is valid for source work only, not physical KMS or HDCP evidence.

## Safety and legal boundary

Do not extract or transmit content keys; copy or replay credentials; use leaked SDKs or private certificates; spoof a security level; force a premium manifest; save protected media outside its permitted path; redistribute proprietary CDMs or Windows system binaries; log production license bodies, private challenges, certificates, decrypted samples, or CDM memory; report `Content Protection = Enabled` before authoritative authentication and encryption; return fake `S_OK`; or publish external security-sensitive material without approval for that target.

Use source inspection, clear media, synthetic patterns, official test vectors, and normal licensed playback.

## Module-load checkpoint

Source work and builds may proceed. Before installing/loading an experimental graphics module, changing boot configuration, or rebooting, complete `docs/recovery/native-test-recovery-checklist.md` and obtain explicit approval.

## Evidence discipline

Every experiment must include a manifest, exact commands, raw stdout/stderr, artifact hashes, a verdict, negative controls, limitations, and the highest state actually proven. Never overwrite raw evidence. One concept per commit.
