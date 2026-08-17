# Read-only HDCP source review

Review date: 2026-08-17

## Result

The implementation is source-complete and repeatedly builds as a full NVIDIA module set against generic Linux headers. It is not runtime-tested.

## Layered changes

1. DisplayPort/RM owner: raw state query with exact RM status and consolidated flags.
2. NVKMS: dedicated append-only private ioctl with detailed failure result.
3. KAPI: append-only read-only function and state structure.
4. `nvidia-drm`: default-off, read-only module parameter and structured log line.

## Corrections found during review/build

- Replaced a malformed hand-authored mail patch with a mechanically checked unified diff.
- Re-anchored the patch to exact 610.57.04 source rather than truncated excerpts.
- Removed nonexistent per-version state words; 610.57.04 returns one consolidated `flags` word.
- Made patch application fail closed rather than falling through to a misleading build.
- Fixed a CI `grep -q`/`pipefail` SIGPIPE false failure.
- Moved the experimental ioctl and KAPI function to append-only positions so existing numeric values and function offsets remain unchanged.

## Safety findings

- No call to `_RENEGOTIATE`, `_SET_TYPE`, `HDCP_CTRL`, or any other control operation was added.
- No standard KMS content-protection property was attached.
- The parameter defaults off and is read-only after module load.
- Unsupported routes, missing DP objects, RM failure, invalid data, and transport failure remain distinguishable.
- The diagnostic logs no key, certificate, challenge, license, media sample, EDID, account, or machine-unique identifier.

## Remaining uncertainty

Only native hardware execution can determine whether the normal GeForce Linux RM/GSP configuration authorizes and returns meaningful HDCP state.
