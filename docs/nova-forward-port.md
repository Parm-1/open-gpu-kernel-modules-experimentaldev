# Nova forward-port track

Nova is a long-term upstream-native target, not the first feasibility path.

## Rationale

The shipping NVIDIA open-module stack already contains DP HDCP behavior that can serve as a reference oracle. Nova's display stack is earlier and should not block the shortest experiment on the RTX 2060.

## Mapping ledger

| Required semantic | Shipping stack | Nova equivalent |
|---|---|---|
| Query receiver/repeater capability | `GET_HDCP_STATE` path | UNKNOWN |
| Query authenticated/encrypting | DP main-link state query | UNKNOWN |
| Select Type 0/Type 1 | `HDCP_CTRL / SET_TYPE` | UNKNOWN |
| Renegotiate authentication | `HDCP_CTRL / RENEGOTIATE` | UNKNOWN |
| Validate link integrity | `HDCP_CTRL / VALIDATE_LINK` | UNKNOWN |
| Receive auth/link-loss event | DP timers/events | UNKNOWN |
| Standard KMS property bridge | missing in `nvidia-drm` | future `nova-drm` design |

Only document public interfaces and observed semantics. Do not copy credentials, licensed protocol material, or vendor-only secrets. Revisit implementation after the shipping-stack experiment yields a truthful state machine and Nova has a mature display/GSP interface.
