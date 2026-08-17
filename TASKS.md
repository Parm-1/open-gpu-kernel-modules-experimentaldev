# Task ledger

Statuses: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `KILLED`.

| ID | Status | Task | Exit evidence |
|---|---|---|---|
| A-001 | DONE | Pin NVIDIA, Chromium, and Wine source baselines | `SOURCES.lock.md` |
| A-002 | DONE | Reproduce NVIDIA HDCP source transition | CI and EXP-0001 |
| A-003 | DONE | Map NVIDIA call-graph discontinuity | architecture documents |
| A-004 | DONE | Resolve NVKMS display-to-DP-library owner | compiled `NVDpyEvo → pDpLibConnector → mainLink` bridge |
| B-001 | DONE | Implement read-only NVKMS HDCP state query | four compiled source commits and source review |
| B-002 | BLOCKED | Run read-only query on native RTX 2060 | recovery checklist, approval, EXP-0006 raw evidence |
| B-003 | BLOCKED | Request Type 0/Type 1 authentication | Gate 1 must pass first |
| B-004 | BLOCKED | Attach standard KMS properties | Gate 2 must pass first |
| C-001 | DONE | Add protected Vulkan capability probe skeleton | probe builds in CI |
| C-002 | BLOCKED | Run Vulkan probe on target stack | native Linux execution |
| C-003 | BLOCKED | Protected swapchain/video-session tests | C-002 results |
| D-001 | DONE | Add safe EME capability probe | local HTML probe |
| D-002 | DONE | Add safe Windows reference collector | PowerShell collector |
| D-003 | BLOCKED | Collect same-hardware Windows baseline | Windows execution |
| E-001 | TODO | Build minimal `mfcdm-probe.exe` | deterministic Windows/Wine first-failure trace |
| E-002 | BLOCKED | Implement Wine PMP boundary | E-001 call graph |
| F-001 | BLOCKED | Weston protected-surface proof | truthful KMS HDCP backend |
| G-001 | BLOCKED | Prepare NVIDIA technical packet | Gate 1 verdict |
| N-001 | DONE | Record Nova as a secondary track | `docs/nova-forward-port.md` |
| N-002 | TODO | Track Nova display/GSP interfaces | maintained mapping table |

## Priority order

1. Review and merge the compile-tested read-only implementation PR.
2. Prepare the native test machine and rollback path.
3. Run Gate 0 and EXP-0006 only after explicit load/reboot approval.
4. Classify Gate 1 before any control or KMS-property work.
