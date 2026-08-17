# NVIDIA DisplayPort HDCP source timeline

Status: `PROVEN_SOURCE`

## Control: 590.48.01

- Commit: `2ccbad25e1af6a6ee6f38cf569f89f8b65d658ab`
- File: `src/common/displayport/src/dp_evoadapter.cpp`
- Symbol: `EvoMainLink::configureHDCPGetHDCPState`
- Finding: the function contains `// HDCP Not Supported` and sets capability, authentication, and encryption fields false. `configureHDCPRenegotiate` is empty.

## Transition: 595.44.02

- Commit: `2c7bfb47060233bda7c37c8065c0ddcac0d3da05`
- Same file and symbols
- Finding: the function calls `NV0073_CTRL_CMD_SPECIFIC_GET_HDCP_STATE`; related methods call `NV0073_CTRL_CMD_SPECIFIC_HDCP_CTRL` for renegotiation and control.

## Current baseline: 610.57.04

- Commit: `e4a5faa2567f28c8eabe0ebb6422b6d0abcf37eb`
- Files:
  - `src/common/displayport/src/dp_evoadapter.cpp`
  - `src/common/displayport/src/dp_groupimpl.cpp`
  - `src/common/sdk/nvidia/inc/ctrl/ctrl0073/ctrl0073specific.h`
- Findings:
  - HDCP 1.x and 2.2 receiver/repeater capability parsing
  - authenticated and encrypting state parsing
  - renegotiate, disable, abort, and validate-link commands
  - Type 0/Type 1 stream selection through `_SET_TYPE`
  - DP group authentication retries and encrypted-stream management

## Reproduction

```bash
scripts/verify-source-transition.sh artifacts/source-transition
```

The script records line-numbered excerpts and hashes from all three revisions. Presence of this source is not evidence that the target Linux RM/GSP product configuration authorizes the operation.
