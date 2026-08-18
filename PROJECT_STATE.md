# Authoritative project state

Last updated: 2026-08-18

## Baseline

- Repository: `Parm-1/open-gpu-kernel-modules-experimentaldev`
- NVIDIA source release: `610.57.04`
- Upstream source baseline: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Read-only implementation merge: `e9507b77cd2075c82ad34353660666ae58ccf502`
- Final implementation head: `de4bc76f4c9f1575b3527f95da719c5e1cb7e708`
- Runtime-readiness merge: `3099029dda066e0545267660b8e4e470655b20ba`
- Runtime-readiness implementation head: `94a50cc2b6199b9804c30bbf2a101278742e5134`
- MF CDM first-failure implementation head: `f1960bfb3583e9b09d56f9fe5cf87af91e3c40bf`
- MF CDM first-failure merge to `main`: `f02b89aa276aba85959bbb942b8f14e9ef40e23b`
- Target GPU: GeForce RTX 2060 (Turing)
- Initial route: direct DisplayPort SST, one display, SDR 1920×1080 60 Hz

## Current gate

**Gate 0 hardware baseline: EXTERNALLY BLOCKED — no native Linux boot with physical RTX 2060 connector ownership is reachable from any environment this project has operated in so far (see [DECISION-0005](docs/decisions/DECISION-0005-gate1-blocked-pending-native-access.md))**

**Gate 1 read-only query implementation: MERGED / FULL-MODULE-BUILD-PASSED / RUNTIME-NOT-RUN**

**Gate 1 runtime readiness: MERGED / TOOLING-COMPLETE / NATIVE-PREFLIGHT-NOT-RUN**

**Gate 1 verdict: cannot be reached without operator action — run EXP-0006 on the physical machine, or grant remote access to one**

Highest NVIDIA security state proven remains `SOURCE_PRESENT`. Generic-header compilation, runtime-tool self-tests, module-identity validation, and protocol preparation do not prove `CAPABILITY_ADVERTISED` on the RTX 2060.

## Compiled NVIDIA implementation

- `cd5f5634d552963e1a713306942c57f505b28740` — DisplayPort/RM-owned read-only raw state query.
- `6918273d53ecf844b7495b94dec902049a61bb59` — dedicated NVKMS ioctl and KAPI path.
- `eb6cb2f4dc052709a3bc2445e962c8c9c97d1d51` — default-off `nvidia-drm` structured diagnostic.
- `3759ee6d4fd9c0d13a69d18e988d8409f303e1d0` — append-only ABI ordering correction.
- `de4bc76f4c9f1575b3527f95da719c5e1cb7e708` — final implementation head; all six checks passed, including complete module compilation.
- `e9507b77cd2075c82ad34353660666ae58ccf502` — implementation merge to `main`.
- `3099029dda066e0545267660b8e4e470655b20ba` — fail-closed EXP-0006 runtime-readiness merge.

No experimental module has been installed or loaded, no boot configuration has changed, and no reboot has been performed.

## EXP-0006 runtime readiness

The repository contains a command-confined native preflight, exact-kernel clean-build packager, loaded-module verifier, machine-specific rollback renderer, minimized baseline collector, operation-scoped approval record, and three-clean-boot protocol: one default-off negative control and two enabled replications.

The next NVIDIA evidence must come from the native RTX 2060 machine under that protocol. Authentication, Type 0/Type 1 selection, KMS content-protection properties, HDMI, MST, protected decode, and service testing remain blocked.

## Media Foundation CDM discovery track

E-001 is source-complete and Windows-build-passed at `f1960bfb3583e9b09d56f9fe5cf87af91e3c40bf`, merged to `main` at `f02b89aa276aba85959bbb942b8f14e9ef40e23b` (PR #4).

The probe uses only public Windows SDK interfaces and stops at:

```text
COM → MFStartup → Media Engine factory → IMFMediaEngineClassFactory4
    → optional explicit CDM factory → IsTypeSupported
```

It contains no default vendor key system and performs no CDM access, CDM/session, request, license, network, media, or playback operation. MSVC warnings-as-errors, deterministic self-tests, source-policy checks, and direct PE-import checks passed.

Native Windows and Wine runtime traces remain `NOT_RUN`; E-002 remains blocked until an identical executable hash and exact input produce a paired first-failure comparison.

## Next evidence-producing actions

1. Run the read-only EXP-0006 preflight on the native RTX 2060 machine and complete the exact-build/recovery package. **Requires operator action — no environment this project has run in so far has physical access to the target machine.**
2. Execute the default-off and two enabled EXP-0006 sessions only after operation-scoped approval.
3. Collect EXP-0007 infrastructure-only traces on native Windows and Wine with the same built executable hash (same access requirement as above).
4. Only after the infrastructure comparison, decide whether a separately recorded explicit key-system/type query is justified.
5. Do not begin NVIDIA authentication/KMS work or Wine PMP implementation before their respective evidence gates pass.
6. Until native access exists, advance N-002 (Nova interface tracking) and other non-hardware tasks per [DECISION-0005](docs/decisions/DECISION-0005-gate1-blocked-pending-native-access.md).
