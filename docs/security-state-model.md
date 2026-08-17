# Security-state model

Use these exact terms in code, logs, experiments, issues, and pull requests.

| State | Meaning |
|---|---|
| `SOURCE_PRESENT` | Relevant code or constants exist in source. |
| `CAPABILITY_ADVERTISED` | A runtime API reports a capability. |
| `REQUEST_ACCEPTED` | A runtime component accepts a request. |
| `AUTHENTICATED` | The protected-link or DRM protocol reports successful authentication. |
| `ENCRYPTING` | The link or content path reports active encryption. |
| `TYPE1_ACTIVE` | The active link is authenticated and encrypting the requested Type 1 stream. |
| `PROTECTED_MEMORY` | GPU resources satisfy a documented protected-memory contract. |
| `PROTECTED_DECODE` | Decode consumes and produces protected resources without a readable clear path. |
| `PROTECTED_PRESENT` | Protected output reaches the display without entering an ordinary capturable surface. |
| `SOFTWARE_ISOLATED` | Process isolation exists, but no hardware-security claim is made. |
| `HARDWARE_PROTECTED` | The measured path uses documented hardware protection. |
| `VENDOR_ATTESTED` | A DRM vendor recognizes the implementation at the required hardware security level. |
| `SERVICE_AUTHORIZED` | The streaming service grants the premium representation. |
| `END_TO_END_PROVEN` | Every required layer is active together and reproduced after a clean reboot. |

Forbidden shortcuts:

- `SOURCE_PRESENT` does not imply `CAPABILITY_ADVERTISED`.
- `REQUEST_ACCEPTED` does not imply `AUTHENTICATED`.
- `AUTHENTICATED` does not imply `ENCRYPTING`.
- HDCP does not imply protected decode or memory.
- `HARDWARE_PROTECTED` does not imply `VENDOR_ATTESTED`.
- `VENDOR_ATTESTED` does not imply `SERVICE_AUTHORIZED`.
