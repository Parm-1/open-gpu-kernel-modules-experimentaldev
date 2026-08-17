# Task ledger

Statuses: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `KILLED`.

| ID | Status | Task | Exit evidence |
|---|---|---|---|
| A-001 | DONE | Pin NVIDIA, Chromium, and Wine source baselines | `SOURCES.lock.md` |
| A-002 | DONE | Reproduce NVIDIA HDCP source transition | source verification script and EXP-0001 |
| A-003 | DONE | Map current NVIDIA call-graph discontinuity | architecture documents |
| A-004 | IN_PROGRESS | Resolve exact NVKMS-to-DP-library state owner | symbol-level design reviewed against source |
| B-001 | TODO | Implement read-only NVKMS HDCP state query | EXP-0006 build + runtime trace |
| B-002 | BLOCKED | Query target RTX 2060 over native Linux DP | target machine and recovery checklist |
| B-003 | BLOCKED | Request Type 0/Type 1 authentication | Gate 1 must pass first |
| B-004 | BLOCKED | Attach standard KMS properties | Gate 2 must pass first |
| C-001 | DONE | Add protected Vulkan capability probe skeleton | probe builds in CI |
| C-002 | BLOCKED | Run Vulkan probe on target NVIDIA Linux stack | native Linux execution |
| C-003 | BLOCKED | Protected swapchain/video-session tests | C-002 results and WSI test harness |
| D-001 | DONE | Add safe EME capability probe | local HTML probe |
| D-002 | DONE | Add safe Windows reference collector | PowerShell collector |
| D-003 | BLOCKED | Collect same-hardware Windows baseline | Windows target execution |
| E-001 | TODO | Build minimal `mfcdm-probe.exe` | deterministic Windows/Wine first-failure trace |
| E-002 | BLOCKED | Implement Wine PMP boundary | E-001 call graph |
| F-001 | BLOCKED | Weston protected-surface proof | truthful KMS HDCP backend |
| G-001 | BLOCKED | Prepare NVIDIA technical packet | Gate 1 verdict |
| N-001 | DONE | Record Nova as a secondary track | `docs/nova-forward-port.md` |
| N-002 | TODO | Track Nova display/GSP interfaces | maintained mapping table |

## Priority order

1. Complete A-004.
2. Implement and review B-001 without loading it.
3. Collect Gate 0 hardware baselines.
4. Build the exact target-kernel module only after recovery preparation.
5. Run B-001 and classify the Gate 1 result.
