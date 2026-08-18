# Task ledger

Statuses: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `KILLED`.

| ID | Status | Task | Exit evidence |
|---|---|---|---|
| A-001 | DONE | Pin NVIDIA, Chromium, and Wine source baselines | `SOURCES.lock.md` |
| A-002 | DONE | Reproduce NVIDIA HDCP source transition | CI and EXP-0001 |
| A-003 | DONE | Map NVIDIA call-graph discontinuity | architecture documents |
| A-004 | DONE | Resolve NVKMS display-to-DP-library owner | compiled `NVDpyEvo → pDpLibConnector → mainLink` bridge |
| B-001 | DONE | Implement and merge read-only NVKMS HDCP state query | PR #2, merge `e9507b77...`, full module build |
| B-002A | DONE | Prepare native EXP-0006 preflight, exact-kernel build, loaded-identity, rollback, baseline, approval, and replication tooling | PR #3, merge `3099029d...` |
| B-002B | BLOCKED | Complete native-machine preflight and exact-kernel recovery package | zero preflight blockers, warnings resolved, offline rollback, approved build manifest |
| B-002C | BLOCKED | Run default-off and two enabled EXP-0006 sessions on the RTX 2060 | three clean-boot sessions, verified restoration, raw evidence, Gate 1 verdict |
| B-003 | BLOCKED | Request Type 0/Type 1 authentication | Gate 1 must pass first |
| B-004 | BLOCKED | Attach standard KMS properties | Gate 2 must pass first |
| C-001 | DONE | Add protected Vulkan capability probe skeleton | probe builds in CI |
| C-002 | BLOCKED | Run Vulkan probe on target stack | native Linux execution |
| C-003 | BLOCKED | Protected swapchain/video-session tests | C-002 results |
| D-001 | DONE | Add safe EME capability probe | local HTML probe |
| D-002 | DONE | Add safe Windows reference collector | PowerShell collector |
| D-003 | BLOCKED | Collect same-hardware Windows baseline | Windows execution |
| E-001 | DONE | Build minimal license-free `mfcdm-probe.exe` | public-SDK source, Windows `/W4 /WX` build, self-test, source/import checks, EXP-0007 |
| E-002 | BLOCKED | Implement Wine PMP boundary | paired native-Windows/Wine EXP-0007 first-failure trace |
| F-001 | BLOCKED | Weston protected-surface proof | truthful KMS HDCP backend |
| G-001 | BLOCKED | Prepare NVIDIA technical packet | Gate 1 verdict |
| N-001 | DONE | Record Nova as a secondary track | `docs/nova-forward-port.md` |
| N-002 | TODO | Track Nova display/GSP interfaces | maintained mapping table |

## Priority order

1. Run the read-only EXP-0006 preflight on the native RTX 2060 machine.
2. Resolve version, identity, signing, recovery, and topology blockers and create the exact-kernel build package.
3. Run the EXP-0006 negative control and two enabled clean-boot replications only after approval.
4. Collect the EXP-0007 infrastructure-only trace on native Windows and Wine using the identical executable hash.
5. Classify Gate 1 and the Wine first-failure boundary before any authentication, KMS-property, or PMP implementation.
6. While native execution is blocked, advance N-002 in a separate change.
