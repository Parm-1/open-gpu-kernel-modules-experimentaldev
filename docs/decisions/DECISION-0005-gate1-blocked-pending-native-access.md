# DECISION-0005: Gate 1 is externally blocked pending native RTX 2060 access

Status: Accepted — 2026-08-18

## Decision

Treat Gate 0 (reproducible hardware baseline) and Gate 1 (read-only NVIDIA
HDCP state) as **externally blocked**, not merely incomplete. Do not attempt
to advance either gate from an environment that lacks a native Linux boot
with physical ownership of the target RTX 2060's DisplayPort connector.
Redirect available effort to workstreams that do not require that access
(N-002 Nova interface tracking, remaining documentation, CI/tooling
reliability) until the operator either runs the existing EXP-0006 protocol
on the real machine or grants remote access to one.

This is a scope/access classification, not a technical verdict on HDCP
support. It must not be read as `VENDOR_BACKEND_BLOCKED` or
`NARROW_NVIDIA_HOOK_REQUIRED` — those verdicts require an actual query
attempt against RM/GSP, which has not happened. The correct current label
for the query result itself remains `UNKNOWN` (EV-0013, EV-0019, EV-0020).

## Reason

Charter §6 requires native Linux boot with physical connector ownership for
any Gate 0/1 evidence; §17 requires explicit operator approval before
loading an experimental module, altering boot configuration, or rebooting.
The repository's own EXP-0006 protocol (`docs/runtime/EXP-0006-native-protocol.md`)
already encodes this: preflight, exact-kernel build, rollback package,
approval record, then three clean-boot sessions on the target machine.

The session that reached this decision runs from a Windows desktop with no
attached Linux boot, no SSH target, and no RTX 2060-bearing machine
reachable from it. WSL is explicitly disqualified by charter §6 for this
purpose (no physical DRM/KMS connector ownership). Continuing to search for
a way to satisfy Gate 1 from this environment would either stall on a
false precondition or risk skipping the recovery/approval discipline the
charter treats as mandatory before any module load — both worse outcomes
than stopping cleanly and naming the blocker.

## What was actually advanced this session

- PR #4 (`agent/mfcdm-first-failure-probe`) was fixed and merged at
  `f02b89aa276aba85959bbb942b8f14e9ef40e23b`. Its CI had been failing for
  a reason unrelated to the probe's own logic or security boundary: a
  PowerShell/GitHub Actions pwsh quirk where a step exits with the last
  native command's stale non-zero `$LASTEXITCODE` even when every
  in-script check passed. Root-caused by reproducing the exact CI
  commands against a local MSVC build before touching the workflow, and
  confirmed by three iterations of a real CI run (two red under
  successive incorrect hypotheses, one green under the correct one).
  E-001 / EXP-0007's Windows build track is now `PROVEN_BUILD` on `main`,
  matching what `PROJECT_STATE.md` and `EVIDENCE.md` already recorded in
  anticipation of this merge.
- Task N-002 ("track Nova display/GSP interfaces") remains the priority-
  ordered fallback work (`TASKS.md` §Priority order, item 6) while native
  execution stays blocked, and is unaffected by this decision.

## What remains blocked and needs operator action

`B-002B` / `B-002C` (native EXP-0006 preflight and the three clean-boot
sessions), `C-002` (Vulkan probe on the real driver stack), `D-003`
(same-hardware Windows baseline), and `E-002`'s runtime half (paired
native-Windows/Wine EXP-0007 traces) all require hands-on-hardware
execution this environment cannot perform. The next evidence-producing
action is still, as `PROJECT_STATE.md` already states, to run the
EXP-0006 preflight on the physical RTX 2060 machine.
